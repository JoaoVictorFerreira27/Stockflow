"""
app.py
StockFlow - Sistema de Controle de Estoque com Automação de Dados
Aplicação Flask principal: define as rotas web (dashboard, CRUD de produtos,
importação/exportação de CSV).
"""

from flask import Flask, render_template, request, redirect, url_for, flash, Response

import database
import data_automation

app = Flask(__name__)
app.secret_key = "dev-secret-key-troque-em-producao"

database.init_db()


@app.route("/")
def dashboard():
    metrics = database.get_dashboard_metrics()
    history = database.get_import_history(limit=5)
    return render_template("dashboard.html", metrics=metrics, history=history)


@app.route("/produtos")
def products():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    items = database.list_products(search=search, category=category)
    categories = database.get_categories()
    return render_template(
        "products.html", products=items, categories=categories, search=search, selected_category=category
    )


@app.route("/produtos/novo", methods=["GET", "POST"])
def new_product():
    if request.method == "POST":
        ok, error = _save_product_from_form()
        if ok:
            flash("Produto cadastrado com sucesso.", "success")
            return redirect(url_for("products"))
        flash(error, "error")
    return render_template("product_form.html", product=None)


@app.route("/produtos/<int:product_id>/editar", methods=["GET", "POST"])
def edit_product(product_id):
    product = database.get_product(product_id)
    if not product:
        flash("Produto não encontrado.", "error")
        return redirect(url_for("products"))

    if request.method == "POST":
        ok, error = _save_product_from_form(product_id=product_id)
        if ok:
            flash("Produto atualizado com sucesso.", "success")
            return redirect(url_for("products"))
        flash(error, "error")

    return render_template("product_form.html", product=product)


@app.route("/produtos/<int:product_id>/excluir", methods=["POST"])
def delete_product(product_id):
    database.delete_product(product_id)
    flash("Produto excluído.", "success")
    return redirect(url_for("products"))


def _save_product_from_form(product_id=None):
    """Valida os dados vindos do formulário de produto e salva no banco."""
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip() or "Geral"

    if not name:
        return False, "O nome do produto é obrigatório."

    try:
        quantity = int(request.form.get("quantity", "0"))
        min_stock = int(request.form.get("min_stock", "0"))
        unit_price = round(float(request.form.get("unit_price", "0")), 2)
        if quantity < 0 or min_stock < 0 or unit_price < 0:
            raise ValueError
    except ValueError:
        return False, "Quantidade, estoque mínimo e preço devem ser números válidos e não-negativos."

    if product_id:
        database.update_product(product_id, name, category, quantity, min_stock, unit_price)
    else:
        database.create_product(name, category, quantity, min_stock, unit_price)
    return True, None


# ---------------------------------------------------------------------------
# Automação de dados: importar / exportar CSV
# ---------------------------------------------------------------------------

@app.route("/importar", methods=["GET", "POST"])
def import_products():
    report = None
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Selecione um arquivo CSV.", "error")
            return redirect(url_for("import_products"))
        try:
            report = data_automation.import_csv(file, file.filename)
            flash(
                f"Importação concluída: {report['rows_imported']} produtos importados, "
                f"{report['rows_rejected']} rejeitados.",
                "success" if report["rows_rejected"] == 0 else "warning",
            )
        except ValueError as e:
            flash(str(e), "error")
    return render_template("import.html", report=report)


@app.route("/exportar/produtos")
def export_products():
    csv_bytes = data_automation.export_csv()
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=produtos_stockflow.csv"},
    )


@app.route("/exportar/estoque-baixo")
def export_low_stock():
    csv_bytes = data_automation.export_low_stock_report()
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=estoque_baixo_stockflow.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
