#!/usr/bin/env python3
"""
Script de validación para el Orquestador LangChain/LangGraph.

Ejecuta una serie de tests para verificar que el sistema completo funciona:
1. Verifica conectividad a sockets MCP
2. Prueba Router Agent con get_schema()
3. Prueba Agentes Especializados (SQL + NoSQL)
4. Prueba Orquestación completa

Uso:
    python3 test_orchestrator.py

O con queries específicas:
    python3 test_orchestrator.py --query "tu pregunta aquí"
"""

import asyncio
import json
import sys
import os
from pathlib import Path


async def test_sockets():
    """Verifica que los Unix sockets están disponibles."""
    print("📡 TEST 1: Verificar sockets MCP...")
    
    sockets = [
        "/tmp/mcp-sockets/sql.sock",
        "/tmp/mcp-sockets/nosql.sock"
    ]
    
    for sock in sockets:
        if Path(sock).exists():
            print(f"  ✅ {sock} disponible")
        else:
            print(f"  ❌ {sock} NO disponible")
            print("     Solución: Ejecuta 'cd ../Ej1-MCPServers && docker compose up -d'")
            return False
    
    return True


async def test_agent_imports():
    """Verifica que se pueden importar los agentes."""
    print("\n📦 TEST 2: Importar agentes especializados...")
    
    try:
        from agent_sql_langchain import execute_sql_query
        print("  ✅ agent_sql_langchain importado")
    except ImportError as e:
        print(f"  ❌ Error importando agent_sql_langchain: {e}")
        return False
    
    try:
        from agent_nosql_langchain import list_collections, query_mongo
        print("  ✅ agent_nosql_langchain importado")
    except ImportError as e:
        print(f"  ❌ Error importando agent_nosql_langchain: {e}")
        return False
    
    try:
        from orchestrator_langchain import run_orchestrator
        print("  ✅ orchestrator_langchain importado")
    except ImportError as e:
        print(f"  ❌ Error importando orchestrator_langchain: {e}")
        return False
    
    return True


async def test_ollama_credentials():
    """Verifica que las credenciales de Ollama están configuradas."""
    print("\n🔑 TEST 3: Validar credenciales Ollama...")
    
    ollama_api_key = os.getenv("OLLAMA_API_KEY")
    if not ollama_api_key:
        print("  ❌ OLLAMA_API_KEY no está definida")
        print("     Solución: export OLLAMA_API_KEY='tu_token_aqui'")
        return False
    
    if len(ollama_api_key) < 20:
        print("  ⚠️  OLLAMA_API_KEY parece incompleta")
        return False
    
    print("  ✅ OLLAMA_API_KEY definida")
    
    model = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
    print(f"  ✅ Modelo: {model}")
    
    return True


async def test_sql_agent():
    """Prueba el agente SQL directamente."""
    print("\n🗄️  TEST 4: Agente SQL...")
    
    try:
        from agent_sql_langchain import execute_sql_query
        
        result = await execute_sql_query("SELECT COUNT(*) as total FROM Artist;")
        result_text = str(result)
        
        if "total" in result_text.lower() or "error" not in result_text.lower():
            print(f"  ✅ SQL Query ejecutada: {result_text[:100]}")
            return True
        else:
            print(f"  ⚠️  SQL Query devolvió: {result_text}")
            return False
    except Exception as e:
        print(f"  ❌ Error en SQL: {e}")
        return False


async def test_nosql_agent():
    """Prueba el agente NoSQL directamente."""
    print("\n📂 TEST 5: Agente NoSQL...")
    
    try:
        from agent_nosql_langchain import list_collections
        
        result = await list_collections()
        result_text = str(result)
        
        if "error" not in result_text.lower():
            print(f"  ✅ MongoDB query ejecutada: {result_text[:100]}")
            return True
        else:
            print(f"  ⚠️  MongoDB query devolvió: {result_text}")
            return False
    except Exception as e:
        print(f"  ❌ Error en NoSQL: {e}")
        return False


async def test_router_with_schema():
    """Prueba el Router Agent con get_schema()."""
    print("\n🔄 TEST 6: Router Agent con get_schema()...")
    
    try:
        from orchestrator_langchain import TOOL_SCHEMAS, build_router_model, get_schema
        
        # Verificar que get_schema devuelve datos
        schema_result = get_schema("sql")
        schema_dict = json.loads(schema_result)
        
        if "tools" in schema_dict:
            print(f"  ✅ get_schema('sql') devuelve herramientas: {schema_dict['tools'][0]['name']}")
        else:
            print("  ❌ get_schema('sql') no devuelve formato esperado")
            return False
        
        schema_result = get_schema("nosql")
        schema_dict = json.loads(schema_result)
        
        if "tools" in schema_dict:
            print(f"  ✅ get_schema('nosql') devuelve herramientas: {schema_dict['tools'][0]['name']}")
        else:
            print("  ❌ get_schema('nosql') no devuelve formato esperado")
            return False
        
        return True
    except Exception as e:
        print(f"  ⚠️  Error en Router: {e}")
        return False


async def test_full_orchestration(query: str):
    """Prueba la orquestación completa."""
    print(f"\n🚀 TEST 7: Orquestación completa")
    print(f"  Query: '{query}'")
    
    try:
        from orchestrator_langchain import run_orchestrator
        
        result = await run_orchestrator(query)
        
        if result and len(str(result)) > 10:
            print(f"  ✅ Resultado: {str(result)[:200]}...")
            return True
        else:
            print(f"  ⚠️  Resultado inesperado: {result}")
            return False
    except Exception as e:
        print(f"  ❌ Error en orquestación: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Ejecuta todos los tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validar Orquestador")
    parser.add_argument("--query", default="Cuantos artistas hay?", help="Query para test de orquestación")
    parser.add_argument("--skip-live", action="store_true", help="Saltar tests que requieren conectividad")
    args = parser.parse_args()
    
    print("=" * 70)
    print("🧪 VALIDACIÓN: ORQUESTADOR LANGCHAIN/LANGGRAPH")
    print("=" * 70)
    
    tests = [
        ("Sockets MCP", test_sockets),
        ("Imports", test_agent_imports),
        ("Ollama Credentials", test_ollama_credentials),
    ]
    
    if not args.skip_live:
        tests.extend([
            ("SQL Agent", test_sql_agent),
            ("NoSQL Agent", test_nosql_agent),
            ("Router + get_schema", test_router_with_schema),
            ("Full Orchestration", lambda: test_full_orchestration(args.query)),
        ])
    
    results = {}
    for name, test_fn in tests:
        try:
            passed = await test_fn()
            results[name] = "✅ PASS" if passed else "❌ FAIL"
        except Exception as e:
            print(f"  ❌ Excepción no capturada: {e}")
            results[name] = "❌ ERROR"
    
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE TESTS:")
    print("=" * 70)
    for name, status in results.items():
        print(f"  {status} {name}")
    
    passed = sum(1 for s in results.values() if "✅" in s)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n✅ ¡Sistema listo! Puedes ejecutar:")
        print(f"   python3 orchestrator_langchain.py --query 'tu pregunta'")
        return 0
    else:
        print("\n❌ Hay tests fallidos. Revisa los errores arriba.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
