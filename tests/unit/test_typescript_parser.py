import importlib.util
import json
from pathlib import Path

import pytest
from feature_graph.sdk.base.plugin_base import PluginManifest, PluginType


def load_ts_plugin():
    manifest_path = Path("plugins/parsers/typescript_parser/plugin.json")
    data = json.loads(manifest_path.read_text())
    spec = importlib.util.spec_from_file_location("ts_plugin", manifest_path.parent / "plugin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Plugin(PluginManifest(**data))


@pytest.mark.asyncio
async def test_typescript_class_and_methods():
    plugin = load_ts_plugin()
    src = """
export class UserService {
  async getUser(id: string): Promise<User | null> { return null; }
  async createUser(data: CreateUserDto): Promise<User> { return {} as User; }
}
"""
    result = await plugin.parse_file("user.service.ts", src)
    names = [s.name for s in result.symbols]
    assert "UserService" in names
    assert "getUser" in names or "createUser" in names


@pytest.mark.asyncio
async def test_typescript_imports():
    plugin = load_ts_plugin()
    src = """
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import axios from 'axios';
"""
    result = await plugin.parse_file("service.ts", src)
    targets = [d.target for d in result.dependencies]
    assert "@nestjs/common" in targets
    assert "axios" in targets


@pytest.mark.asyncio
async def test_typescript_function():
    plugin = load_ts_plugin()
    src = """
export function authenticate(token: string): boolean {
  return token.length > 0;
}
const validate = (x: string) => x.trim() !== '';
"""
    result = await plugin.parse_file("auth.ts", src)
    names = [s.name for s in result.symbols]
    assert "authenticate" in names


@pytest.mark.asyncio
async def test_tsx_component():
    plugin = load_ts_plugin()
    src = """
import React from 'react';
import { Button } from './Button';

export function LoginForm() {
  return <div>Login</div>;
}
"""
    result = await plugin.parse_file("LoginForm.tsx", src)
    names = [s.name for s in result.symbols]
    assert "LoginForm" in names
    targets = [d.target for d in result.dependencies]
    assert "react" in targets or "React" in [s.name for s in result.symbols]


@pytest.mark.asyncio
async def test_language_is_typescript():
    plugin = load_ts_plugin()
    result = await plugin.parse_file("foo.ts", "const x = 1;")
    assert result.language == "typescript"
