#!/usr/bin/env bash
# EJEMPLOS DE USO DEL ORQUESTADOR LANGCHAIN/LANGGRAPH
#
# Archivo: run_examples.sh
# Ejecuta una serie de queries contra el orquestador para demostrar
# la capacidad de router inteligente.
#
# Uso:
#   bash run_examples.sh
#
# Requisitos previos:
#   - Docker containers del Ej1 corriendo (docker compose up -d)
#   - Dependencias instaladas (pip install -r requirements.txt)
#   - OLLAMA_API_KEY exportada

set -e

# Colors para output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================================="
echo "EJEMPLOS DEL ORQUESTADOR LANGCHAIN/LANGGRAPH"
echo "=========================================================="
echo ""

# Verificar que OLLAMA_API_KEY está definida
if [ -z "$OLLAMA_API_KEY" ]; then
    echo -e "${RED}❌ OLLAMA_API_KEY no está definida${NC}"
    echo "    Export: export OLLAMA_API_KEY='tu_api_key_aqui'"
    exit 1
fi

echo -e "${GREEN}✅ OLLAMA_API_KEY encontrada${NC}"
echo ""

# Función para ejecutar ejemplo
run_example() {
    local num=$1
    local category=$2
    local query=$3
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}EJEMPLO $num: $category${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "Query: ${YELLOW}$query${NC}"
    echo ""
    echo "🔄 Ejecutando orquestador..."
    echo ""
    
    python3 orchestrator_langchain.py --query "$query"
    
    echo ""
    echo ""
}

# EJEMPLO 1: SQL Puro
run_example 1 "SQL Puro" \
    "¿Cuantos artistas hay en total en la base de datos Chinook?"

# EJEMPLO 2: NoSQL Puro
run_example 2 "NoSQL Puro" \
    "¿Qué colecciones hay disponibles en MongoDB?"

# EJEMPLO 3: SQL con Análisis
run_example 3 "SQL con Análisis" \
    "¿Cuáles son los géneros más populares en Chinook? Necesito los top 5."

# EJEMPLO 4: Búsqueda Específica
run_example 4 "Búsqueda Específica" \
    "Dame todas las canciones del álbum 'The Dark Side of the Moon'"

# EJEMPLO 5: Combinado (Query que podría ser ambas)
run_example 5 "Query Ambigua / Router Decision" \
    "¿Cada artist tiene cuántos albums en promedio?"

echo ""
echo "=========================================================="
echo -e "${GREEN}✅ TODOS LOS EJEMPLOS EJECUTADOS${NC}"
echo "=========================================================="
echo ""
echo "📝 PRÓXIMOS PASOS:"
echo ""
echo "1. Prueba queries personalizadas:"
echo "   python3 orchestrator_langchain.py --query 'tu pregunta aquí'"
echo ""
echo "2. Ver detalles de arquitectura:"
echo "   cat ARQUITECTURA_ORQUESTADOR.md"
echo ""
echo "3. Validar sistema completo:"
echo "   python3 test_orchestrator.py"
echo ""
echo "4. Entender flujo de MCP:"
echo "   cat FLUJO_CONEXION_MCP.md"
echo ""
