"""
Atomic-level code analysis — extracts business logic from source files.

Uses tree-sitter to decompose a file into:
  - Functions/methods with their signatures
  - Business conditions (if/else/guard clauses)
  - Validation patterns
  - Data flow (inputs → transformations → outputs)
  - Error cases (raise/throw)

No LLM needed — pure structural analysis.
With LLM credits: enriches with plain-English business rule summaries.
"""
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


def _extract_python_logic(source: str, file_path: str) -> list[dict[str, Any]]:
    """Extract business logic atoms from Python source."""
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
        PY = Language(tspython.language())
        parser = Parser(PY)
        tree = parser.parse(source.encode())
    except Exception:
        return _fallback_extract(source, file_path)

    atoms = []

    def walk(node, class_name=None):
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            cname = name_node.text.decode() if name_node else "Unknown"
            for child in node.children:
                walk(child, class_name=cname)
            return

        if node.type in ("function_definition", "decorated_definition"):
            fn_node = node if node.type == "function_definition" else next(
                (c for c in node.children if c.type == "function_definition"), node
            )
            name_node = fn_node.child_by_field_name("name")
            fn_name   = name_node.text.decode() if name_node else "unknown"

            # Get docstring
            body_node = fn_node.child_by_field_name("body")
            docstring = ""
            if body_node and body_node.children:
                first = next((c for c in body_node.children if c.type == "expression_statement"), None)
                if first:
                    s = first.text.decode().strip().strip('"""').strip("'''").strip()
                    if s and len(s) < 300:
                        docstring = s

            # Extract conditions (if statements = business rules)
            conditions = []
            if body_node:
                for child in _iter_all(body_node):
                    if child.type == "if_statement":
                        cond = child.child_by_field_name("condition")
                        if cond:
                            text = cond.text.decode().replace("\n", " ").strip()[:100]
                            conditions.append({"type": "condition", "text": text})
                    elif child.type == "raise_statement":
                        text = child.text.decode().replace("\n", " ").strip()[:100]
                        conditions.append({"type": "error", "text": text})
                    elif child.type == "return_statement":
                        text = child.text.decode().replace("\n", " ").strip()[:80]
                        if text not in ("return", "return None"):
                            conditions.append({"type": "return", "text": text})

            # Parameters
            params_node = fn_node.child_by_field_name("parameters")
            params = []
            if params_node:
                for p in params_node.children:
                    if p.type in ("identifier", "typed_parameter", "default_parameter"):
                        t = p.text.decode().strip()
                        if t not in ("self", "cls", ",", "(", ")"):
                            params.append(t)

            full_name = f"{class_name}.{fn_name}" if class_name else fn_name
            atoms.append({
                "name":        full_name,
                "type":        "method" if class_name else "function",
                "class":       class_name,
                "docstring":   docstring,
                "params":      params[:8],
                "line":        fn_node.start_point[0] + 1,
                "conditions":  conditions[:10],
                "language":    "python",
            })

        for child in node.children:
            if node.type != "class_definition":
                walk(child, class_name)

    walk(tree.root_node)
    return atoms[:30]


def _extract_ruby_logic(source: str, file_path: str) -> list[dict[str, Any]]:
    """Extract business logic atoms from Ruby source."""
    try:
        import tree_sitter_ruby as tsruby
        from tree_sitter import Language, Parser
        RB = Language(tsruby.language())
        parser = Parser(RB)
        tree = parser.parse(source.encode())
    except Exception:
        return _fallback_extract(source, file_path)

    atoms = []

    def walk(node, class_name=None):
        if node.type == "class":
            name_node = node.child_by_field_name("name")
            cname = name_node.text.decode() if name_node else "Unknown"
            for child in node.children:
                walk(child, class_name=cname)
            return

        if node.type == "method":
            name_node = node.child_by_field_name("name")
            fn_name   = name_node.text.decode() if name_node else "unknown"
            body_node = node.child_by_field_name("body")

            conditions, params = [], []

            params_node = node.child_by_field_name("parameters")
            if params_node:
                for p in params_node.children:
                    if p.type in ("identifier", "optional_parameter", "keyword_parameter"):
                        t = p.text.decode().strip().strip(",").strip()
                        if t and t not in ("(", ")", ","):
                            params.append(t)

            if body_node:
                for child in _iter_all(body_node):
                    if child.type == "if":
                        cond = child.child_by_field_name("condition")
                        if cond:
                            text = cond.text.decode().replace("\n", " ").strip()[:100]
                            conditions.append({"type": "condition", "text": text})
                    elif child.type == "raise":
                        text = child.text.decode().replace("\n", " ").strip()[:100]
                        conditions.append({"type": "error", "text": text})

            full_name = f"{class_name}#{fn_name}" if class_name else fn_name
            atoms.append({
                "name":        full_name,
                "type":        "method" if class_name else "function",
                "class":       class_name,
                "docstring":   "",
                "params":      params[:8],
                "line":        node.start_point[0] + 1,
                "conditions":  conditions[:10],
                "language":    "ruby",
            })

        for child in node.children:
            if node.type != "class":
                walk(child, class_name)

    walk(tree.root_node)
    return atoms[:30]


def _fallback_extract(source: str, file_path: str) -> list[dict[str, Any]]:
    """Regex-based fallback when tree-sitter isn't available."""
    atoms = []
    patterns = [
        (r"def\s+(\w+)\s*\(([^)]*)\)", "function", "python"),
        (r"def\s+(\w+)\s*(\([^)]*\))?", "method", "ruby"),
        (r"public\s+\w+\s+(\w+)\s*\(([^)]*)\)", "method", "java"),
    ]
    for pattern, kind, lang in patterns:
        for m in re.finditer(pattern, source):
            fn_name = m.group(1)
            atoms.append({
                "name": fn_name, "type": kind, "class": None,
                "docstring": "", "params": [], "line": source[:m.start()].count("\n") + 1,
                "conditions": [], "language": lang,
            })
    return atoms[:20]


def _iter_all(node):
    yield node
    for child in node.children:
        yield from _iter_all(child)


def _extract_typescript_logic(source: str, file_path: str) -> list[dict[str, Any]]:
    """Extract business logic atoms from TypeScript/JavaScript source."""
    try:
        import tree_sitter_typescript as tsts
        from tree_sitter import Language, Parser
        suffix = Path(file_path).suffix.lower()
        lang = Language(tsts.language_tsx() if suffix in (".tsx", ".jsx") else tsts.language_typescript())
        parser = Parser(lang)
        tree = parser.parse(source.encode())
    except Exception:
        return _fallback_extract(source, file_path)

    atoms = []

    def walk(node, class_name=None):
        if node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            cname = name_node.text.decode() if name_node else "Unknown"
            for child in node.children:
                walk(child, class_name=cname)
            return

        if node.type in ("function_declaration", "method_definition",
                         "function", "arrow_function", "public_field_definition"):
            name_node = node.child_by_field_name("name")
            fn_name   = name_node.text.decode() if name_node else "<anonymous>"

            body_node = node.child_by_field_name("body") or node.child_by_field_name("value")
            conditions, params = [], []

            params_node = node.child_by_field_name("parameters")
            if params_node:
                for p in params_node.children:
                    if p.type in ("required_parameter", "optional_parameter", "identifier"):
                        t = p.text.decode().split(":")[0].strip().strip(",").strip()
                        if t and t not in ("(", ")", ","):
                            params.append(t)

            if body_node:
                for child in _iter_all(body_node):
                    if child.type == "if_statement":
                        cond = child.child_by_field_name("condition")
                        if cond:
                            text = cond.text.decode().replace("\n", " ").strip()[:100]
                            conditions.append({"type": "condition", "text": text})
                    elif child.type == "throw_statement":
                        text = child.text.decode().replace("\n", " ").strip()[:100]
                        conditions.append({"type": "error", "text": text})
                    elif child.type == "return_statement":
                        text = child.text.decode().replace("\n", " ").strip()[:80]
                        if len(text) > 7:
                            conditions.append({"type": "return", "text": text})

            full_name = f"{class_name}.{fn_name}" if class_name else fn_name
            atoms.append({
                "name":       full_name,
                "type":       "method" if class_name else "function",
                "class":      class_name,
                "docstring":  "",
                "params":     params[:8],
                "line":       node.start_point[0] + 1,
                "conditions": conditions[:10],
                "language":   "typescript",
            })

        for child in node.children:
            if node.type != "class_declaration":
                walk(child, class_name)

    walk(tree.root_node)
    return atoms[:30]


def _fn_action(fn_name: str) -> str:
    base  = fn_name.split(".")[-1].rstrip("?!")
    words = base.replace("_", " ").strip()
    for prefix, repl in [
        ("can ", ""), ("is ", ""), ("has ", ""),
        ("should ", ""), ("will ", ""),
        ("destroy ", "destroying "), ("delete ", "deleting "),
        ("update ", "updating "), ("create ", "creating "),
        ("upload ", "uploading "), ("add ", "adding "),
        ("validate ", "validating "), ("check ", "checking "),
        ("send ", "sending "), ("find ", "finding "),
        ("build ", "building "), ("get ", "getting "),
    ]:
        if words.startswith(prefix):
            remainder = words[len(prefix):]
            return remainder if prefix in ("can ", "is ", "has ", "should ", "will ") else repl + remainder
    return words


def _humanize(condition: str, fn_name: str, rule_type: str) -> str:
    """Full business logic sentence — explains intent and consequence."""
    c       = condition.strip()
    c_clean = (c.replace("self.", "").replace("@", "")
                 .replace(".to_s", "").replace(".to_i", "").replace("!!", ""))
    c_lower = c_clean.lower()
    action  = _fn_action(fn_name)

    # Error / raise
    if rule_type == "error":
        msg_m = re.search(r'["\'\']([^\"\']{4,})["\'\']', c)
        if msg_m:
            return f'Fails with "{msg_m.group(1)}" and aborts the operation'
        return "Raises an error and stops processing"

    # Return
    if rule_type == "return":
        if re.search(r"\bnil\b|\bnull\b|\bNone\b", c):
            return f"Exits early — {action} stops here, nothing returned"
        bool_m = re.search(r"\b(true|false|True|False)\b", c_clean)
        if bool_m:
            outcome = "succeeded" if bool_m.group(1).lower() == "true" else "failed"
            return f"Reports that {action} has {outcome}"
        var = c_clean.strip().lstrip("!").replace("_", " ")
        return f"Returns whether {var} — tells the caller if {action} worked"

    # ENV
    env_m = re.search(r'ENV\[["\']([\w_]+)["\']\]', c)
    if env_m:
        var = env_m.group(1)
        if "match" in c:
            val_m = re.search(r'match\s*[\(/"\']([^/"\')]+)', c)
            env_val = val_m.group(1) if val_m else "production"
            if ".nil?" in c:
                return f"Skipped in '{env_val}' — this step only runs outside production"
            return f"Only {action} when running in '{env_val}' environment"
        return f"Checks the {var} environment configuration before proceeding"

    # params[]
    params = re.findall(r"params\[[:\"']?([\w_]+)[\"']?\]", c)
    if params:
        p = [x.replace("_", " ") for x in params[:3]]
        if any("phone" in x for x in params) and any("country" in x for x in params):
            return ("Country code cannot be submitted without a phone number — "
                    "both must be provided together or both left empty")
        if "view_only" in c.lower():
            return ("When the request is view-only, results are filtered "
                    "to organisations where the user has read-only access")
        if re.search(r"empty|blank|nil", c_lower):
            return f"Aborts if '{p[0]}' is not provided — it is required to continue"
        if "&&" in c:
            return f"Both '{p[0]}' and '{p[1] if len(p)>1 else '…'}' must be provided together"
        return f"Uses '{p[0]}' from the request to determine how to {action}"

    # nil / blank
    if re.search(r"\.nil\?|\.blank\?", c_lower):
        subj_raw = re.split(r"\.(nil|blank)", c_lower)[0].strip().lstrip("!")
        neg = c.strip().startswith("!")
        subj = _format_subject(subj_raw)
        if neg:
            return f"Skips when {subj} has no value — nothing to {action}"
        return f"{subj} must have a value before {action} can run"

    # empty
    if ".empty?" in c_lower:
        subj_raw = c_lower.split(".empty")[0].strip().lstrip("!")
        neg = c.strip().startswith("!")
        subj = _format_subject(subj_raw)
        return (f"{subj} must not be empty — at least one entry is needed to {action}"
                if neg else f"Skips {action} when {subj} is empty")

    # present / any / exists
    if re.search(r"\.present\?|\.any\?|\.exists\?", c_lower):
        subj_raw = re.split(r"\.(present|any|exists)", c_lower)[0].strip()
        return f"{_format_subject(subj_raw)} must already exist before {action} can run"

    # Equality / inequality
    eq_m = re.search(r"(.+?)\s*(!?=+)\s*[\"']*([^\"']+?)[\"']*\s*$", c_clean)
    if eq_m:
        lhs, op, rhs = eq_m.groups()
        subj = _format_subject(lhs.strip())
        is_ne = "!" in op
        if is_ne:
            return f"{subj} must not be '{rhs}' — '{rhs}' records are excluded from {action}"
        return f"Only proceeds when {subj} is set to '{rhs}'"

    # match / regex
    match_m = re.search(r"match\s*[/(\"'](.*?)[/\"\'\)]", c)
    if match_m:
        pattern = match_m.group(1)[:50]
        return f"Validates that the value matches '{pattern}' — rejects if it doesn't"

    # Comparisons
    cmp_m = re.search(r"(.+?)\s*([<>]=?)\s*(.+)", c_clean)
    if cmp_m:
        lhs, op, rhs = cmp_m.groups()
        words = {"<": "below", ">": "above", "<=": "at most", ">=": "at least"}
        return f"{_format_subject(lhs.strip())} must be {words.get(op, op)} {rhs.strip()} to {action}"

    # Simple boolean
    if re.match(r"^!?[a-z_?!]+$", c_clean):
        neg  = c.strip().startswith("!")
        flag = c_clean.lstrip("!").replace("_", " ").rstrip("?!")
        return (f"Skips when '{flag}' is off" if neg else
                f"Proceeds only when '{flag}' is active")

    return f"Condition met: {c_clean[:90]}"


def _format_subject(raw: str) -> str:
    """Turn a snake_case/camelCase code identifier into Title Case words."""
    s = re.sub(r'[_\[\]"\'.()]+', ' ', raw).strip()
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)   # camelCase split
    s = re.sub(r'\s+', ' ', s).strip()
    return s.title() if len(s) < 40 else s[:40]


def _language_from_path(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {".py": "python", ".rb": "ruby", ".ts": "typescript",
            ".tsx": "typescript", ".js": "javascript", ".java": "java"}.get(ext, "unknown")


@router.get("/feature/{feature_id}/atoms")
async def get_feature_atoms(
    feature_id: str,
    request: Request,
    file_path: str = Query(None, description="Specific file to analyze (optional)"),
):
    """
    Atomic-level business logic extraction for a feature.
    Returns functions, conditions, validations, error cases.
    """
    engine = request.app.state.engine

    features = await engine.neo4j.query(
        "MATCH (f:Feature {id: $id}) RETURN f", id=feature_id
    )
    if not features:
        raise HTTPException(status_code=404, detail="Feature not found")

    feature   = features[0]
    src_files = feature.get("source_files", [])
    if file_path:
        src_files = [f for f in src_files if file_path in f or f in file_path] or [file_path]

    repos = await engine.neo4j.query(
        "MATCH (r:Repository) RETURN r.path AS path"
    )
    repo_paths = [r["path"] for r in repos]

    all_atoms: list[dict[str, Any]] = []

    for sf in src_files[:3]:  # analyze up to 3 files
        resolved = None
        for rp in repo_paths:
            # Direct path
            candidate = Path(rp) / sf
            if candidate.exists():
                resolved = candidate
                break
            # Search by filename in repo tree (handles mismatched prefixes)
            fname = Path(sf).name
            for found in Path(rp).rglob(fname):
                if str(found).endswith(sf) or sf.endswith(found.name):
                    resolved = found
                    break
            if resolved:
                break
        if not resolved:
            p = Path(sf)
            if p.exists():
                resolved = p

        if not resolved:
            continue

        try:
            source = resolved.read_text(errors="replace")
            lang   = _language_from_path(sf)

            if lang == "python":
                atoms = _extract_python_logic(source, sf)
            elif lang == "ruby":
                atoms = _extract_ruby_logic(source, sf)
            elif lang == "typescript":
                atoms = _extract_typescript_logic(source, sf)
            else:
                atoms = _fallback_extract(source, sf)

            for a in atoms:
                a["file"] = sf
            all_atoms.extend(atoms)
        except Exception:
            continue

    # Build business rule summary with human-readable explanations
    rules = []
    for atom in all_atoms:
        for cond in atom.get("conditions", []):
            raw_text = cond["text"]
            readable = _humanize(raw_text, atom["name"], cond["type"])
            rules.append({
                "function":      atom["name"],
                "rule_type":     cond["type"],
                "description":   raw_text,        # raw code condition
                "readable":      readable,          # plain-English explanation
                "file":          atom.get("file", ""),
                "line":          atom.get("line", 0),
            })

    return {
        "feature_name": feature.get("name"),
        "files_analyzed": len(set(a.get("file") for a in all_atoms)),
        "functions": all_atoms,
        "business_rules": rules,
        "rule_count": len(rules),
        "function_count": len(all_atoms),
    }
