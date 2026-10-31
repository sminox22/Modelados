"""
Evaluador seguro de funciones f(x) para graficar, usando el mismo enfoque
basado en ast (sin eval directo) que utils/calculator.py, pero evaluando
sobre arreglos de NumPy para poder graficar la función completa.
"""
import ast
import math

import numpy as np

from utils.exceptions import CalculoError

_OPERADORES_PERMITIDOS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
    ast.Mod: lambda a, b: a % b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}

_FUNCIONES_PERMITIDAS = {
    "sqrt": np.sqrt,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "log": np.log10,
    "ln": np.log,
    "abs": np.abs,
    "exp": np.exp,
    "pi": math.pi,
    "e": math.e,
}


def evaluar_funcion(expresion: str, valores_x: np.ndarray) -> np.ndarray:
    """
    Evalúa f(x) para un arreglo de valores de x. Acepta 'x' como variable,
    '^' como potencia y funciones básicas (sin, cos, tan, sqrt, log, etc).
    """
    if not expresion or not expresion.strip():
        raise CalculoError("Ingrese una función, por ejemplo: x^2 - 3*x + 2")

    expresion_normalizada = expresion.replace("^", "**")

    try:
        arbol = ast.parse(expresion_normalizada, mode="eval")
        with np.errstate(all="ignore"):
            resultado = _evaluar_nodo(arbol.body, valores_x)
        if np.isscalar(resultado):
            resultado = np.full_like(valores_x, resultado, dtype=float)
        return resultado
    except CalculoError:
        raise
    except Exception:
        raise CalculoError(
            "No se pudo interpretar la función. Use 'x' como variable, "
            "por ejemplo: x^2 - 3*x + 2, sin(x), sqrt(x)"
        )


def _evaluar_nodo(nodo, x):
    if isinstance(nodo, ast.Constant):
        if isinstance(nodo.value, (int, float)):
            return nodo.value
        raise CalculoError("Valor no permitido en la función.")

    if isinstance(nodo, ast.BinOp):
        tipo_operador = type(nodo.op)
        if tipo_operador not in _OPERADORES_PERMITIDOS:
            raise CalculoError("Operador no permitido.")
        izquierda = _evaluar_nodo(nodo.left, x)
        derecha = _evaluar_nodo(nodo.right, x)
        return _OPERADORES_PERMITIDOS[tipo_operador](izquierda, derecha)

    if isinstance(nodo, ast.UnaryOp):
        tipo_operador = type(nodo.op)
        if tipo_operador not in _OPERADORES_PERMITIDOS:
            raise CalculoError("Operador no permitido.")
        valor = _evaluar_nodo(nodo.operand, x)
        return _OPERADORES_PERMITIDOS[tipo_operador](valor)

    if isinstance(nodo, ast.Call):
        if not isinstance(nodo.func, ast.Name) or nodo.func.id not in _FUNCIONES_PERMITIDAS:
            raise CalculoError("Función no permitida.")
        argumentos = [_evaluar_nodo(a, x) for a in nodo.args]
        return _FUNCIONES_PERMITIDAS[nodo.func.id](*argumentos)

    if isinstance(nodo, ast.Name):
        if nodo.id == "x":
            return x
        if nodo.id in _FUNCIONES_PERMITIDAS:
            return _FUNCIONES_PERMITIDAS[nodo.id]
        raise CalculoError(f"Variable o nombre no permitido: '{nodo.id}'. Use 'x'.")

    raise CalculoError("Expresión no válida.")
