"""
data_automation.py
Rotinas de automação de dados: importação/exportação em massa via CSV,
com validação, limpeza e tratamento de inconsistências.

Este módulo é o coração do projeto: em vez de cadastrar produtos um a um,
o usuário sobe uma planilha CSV inteira e o sistema:
  1. Valida cada linha (campos obrigatórios, tipos, valores negativos etc.)
  2. Limpa dados (espaços em branco, capitalização, duplicados)
  3. Importa apenas as linhas válidas
  4. Retorna um relatório do que foi aceito e do que foi rejeitado (e por quê)
"""

import io
import pandas as pd

import database

REQUIRED_COLUMNS = ["name", "category", "quantity", "min_stock", "unit_price"]


def _clean_string(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def validate_and_clean(df: pd.DataFrame):
    """
    Recebe um DataFrame cru vindo do CSV e retorna:
      - clean_rows: lista de dicts prontos para inserir no banco
      - errors: lista de dicts {row, reason} para as linhas rejeitadas
    """
    clean_rows = []
    errors = []
    seen_names = set()

    # Normaliza nomes de colunas (case/espacos) para aceitar CSVs "sujos"
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Colunas obrigatórias ausentes no CSV: {', '.join(missing_cols)}"
        )

    for idx, row in df.iterrows():
        line_number = idx + 2  # +2 = compensa header e index 0-based
        name = _clean_string(row.get("name"))
        category = _clean_string(row.get("category")) or "Geral"

        # --- validações de campos obrigatórios ---
        if not name:
            errors.append({"row": line_number, "reason": "Nome do produto vazio"})
            continue

        # --- deduplicação dentro do próprio arquivo (case-insensitive) ---
        key = name.lower()
        if key in seen_names:
            errors.append({"row": line_number, "reason": f"Duplicado no arquivo: '{name}'"})
            continue

        # --- validação e limpeza de tipos numéricos ---
        try:
            quantity = int(float(row.get("quantity")))
            if quantity < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append({"row": line_number, "reason": "Quantidade inválida ou negativa"})
            continue

        try:
            min_stock = int(float(row.get("min_stock")))
            if min_stock < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append({"row": line_number, "reason": "Estoque mínimo inválido ou negativo"})
            continue

        try:
            unit_price = round(float(row.get("unit_price")), 2)
            if unit_price < 0:
                raise ValueError
        except (TypeError, ValueError):
            errors.append({"row": line_number, "reason": "Preço unitário inválido ou negativo"})
            continue

        # Normaliza capitalização (ex: "arroz" -> "Arroz")
        name = name.title()
        category = category.title()

        seen_names.add(key)
        clean_rows.append(
            {
                "name": name,
                "category": category,
                "quantity": quantity,
                "min_stock": min_stock,
                "unit_price": unit_price,
            }
        )

    return clean_rows, errors


def import_csv(file_storage, filename: str):
    """
    Recebe um arquivo CSV (file-like) do formulário de upload, roda a
    validação/limpeza e insere os produtos válidos no banco.
    Retorna um relatório com contagens e a lista de erros.
    """
    raw_bytes = file_storage.read()
    df = pd.read_csv(io.BytesIO(raw_bytes))

    clean_rows, errors = validate_and_clean(df)

    for row in clean_rows:
        database.create_product(
            row["name"], row["category"], row["quantity"], row["min_stock"], row["unit_price"]
        )

    report = {
        "rows_total": len(df),
        "rows_imported": len(clean_rows),
        "rows_rejected": len(errors),
        "errors": errors,
    }
    database.log_import(filename, report["rows_total"], report["rows_imported"], report["rows_rejected"])
    return report


def export_csv() -> bytes:
    """Exporta todos os produtos cadastrados como CSV (bytes prontos para download)."""
    products = database.list_products()
    df = pd.DataFrame(products)
    if df.empty:
        df = pd.DataFrame(columns=["id", "name", "category", "quantity", "min_stock", "unit_price"])
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def export_low_stock_report() -> bytes:
    """Exporta um relatório CSV apenas com produtos abaixo do estoque mínimo."""
    metrics = database.get_dashboard_metrics()
    df = pd.DataFrame(metrics["low_stock"])
    if df.empty:
        df = pd.DataFrame(columns=["id", "name", "category", "quantity", "min_stock", "unit_price"])
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
