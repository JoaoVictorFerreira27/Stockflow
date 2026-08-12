"""
generate_report.py
Script de automação standalone (fora do Flask) que gera um relatório
resumido do estoque em .txt, para rodar por linha de comando ou agendado
(ex: cron, Task Scheduler) sem precisar subir a aplicação web.

Uso:
    python scripts/generate_report.py
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))

import database  # noqa: E402


def generate_report():
    database.init_db()
    metrics = database.get_dashboard_metrics()

    lines = []
    lines.append(f"RELATÓRIO DE ESTOQUE - StockFlow")
    lines.append(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    lines.append("=" * 50)
    lines.append(f"Total de produtos: {metrics['total_products']}")
    lines.append(f"Valor total em estoque: R$ {metrics['total_value']:.2f}")
    lines.append("")

    lines.append("PRODUTOS POR CATEGORIA")
    lines.append("-" * 50)
    for cat in metrics["by_category"]:
        lines.append(f"  {cat['category']:<20} {cat['total']:>4} itens  |  {cat['units']:>6} unidades")
    lines.append("")

    lines.append("ALERTAS DE ESTOQUE BAIXO")
    lines.append("-" * 50)
    if metrics["low_stock"]:
        for item in metrics["low_stock"]:
            lines.append(
                f"  {item['name']:<25} qtd: {item['quantity']:>4}  (mínimo: {item['min_stock']})"
            )
    else:
        lines.append("  Nenhum item abaixo do estoque mínimo.")

    report_text = "\n".join(lines)

    output_path = Path(__file__).resolve().parent.parent / "data" / "relatorio_estoque.txt"
    output_path.write_text(report_text, encoding="utf-8")

    print(report_text)
    print(f"\nRelatório salvo em: {output_path}")


if __name__ == "__main__":
    generate_report()
