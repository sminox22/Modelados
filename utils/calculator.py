"""
Evaluador seguro de expresiones matemáticas para la calculadora.

No se usa eval() directamente sobre el texto del usuario (riesgo de
seguridad: permitiría ejecutar código arbitrario). En su lugar, se
recorre el árbol sintáctico (ast) y solo se permiten operaciones
aritméticas y funciones matemáticas explícitamente autorizadas.
"""
import ast
import math

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
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log10,
    "ln": math.log,
    "abs": abs,
    "pi": math.pi,
    "e": math.e,
}


def evaluar_expresion(expresion: str) -> float:
    """
    Evalúa de forma segura una expresión aritmética como "2*(3+4)" o
    "sqrt(16) + 2^3" (se acepta '^' como potencia, además de '**').
    Lanza CalculoError si la expresión no es válida.
    """
    if not expresion or not expresion.strip():
        raise CalculoError("Ingrese una operación antes de calcular.")

    expresion_normalizada = expresion.replace("^", "**").replace("×", "*").replace("x", "*").replace("÷", "/")

    try:
        arbol = ast.parse(expresion_normalizada, mode="eval")
        resultado = _evaluar_nodo(arbol.body)
        return resultado
    except CalculoError:
        raise
    except ZeroDivisionError:
        raise CalculoError("No es posible dividir entre cero.")
    except Exception:
        raise CalculoError("Operación no válida. Revise paréntesis y símbolos.")


def _evaluar_nodo(nodo):
    if isinstance(nodo, ast.Constant):
        if isinstance(nodo.value, (int, float)):
            return nodo.value
        raise CalculoError("Valor no permitido en la operación.")

    if isinstance(nodo, ast.BinOp):
        tipo_operador = type(nodo.op)
        if tipo_operador not in _OPERADORES_PERMITIDOS:
            raise CalculoError("Operador no permitido.")
        izquierda = _evaluar_nodo(nodo.left)
        derecha = _evaluar_nodo(nodo.right)
        return _OPERADORES_PERMITIDOS[tipo_operador](izquierda, derecha)

    if isinstance(nodo, ast.UnaryOp):
        tipo_operador = type(nodo.op)
        if tipo_operador not in _OPERADORES_PERMITIDOS:
            raise CalculoError("Operador no permitido.")
        valor = _evaluar_nodo(nodo.operand)
        return _OPERADORES_PERMITIDOS[tipo_operador](valor)

    if isinstance(nodo, ast.Call):
        if not isinstance(nodo.func, ast.Name) or nodo.func.id not in _FUNCIONES_PERMITIDAS:
            raise CalculoError("Función no permitida.")
        argumentos = [_evaluar_nodo(a) for a in nodo.args]
        return _FUNCIONES_PERMITIDAS[nodo.func.id](*argumentos)

    if isinstance(nodo, ast.Name):
        if nodo.id in _FUNCIONES_PERMITIDAS:
            return _FUNCIONES_PERMITIDAS[nodo.id]
        raise CalculoError("Nombre no permitido en la operación.")

    raise CalculoError("Expresión no válida.")
