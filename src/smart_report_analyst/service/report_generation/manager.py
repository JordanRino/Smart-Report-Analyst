from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
import io


def generate_pdf(tool_result, user_question):
    title = tool_result.get("refined_user_question", user_question)
    results = tool_result.get("results", [])
    sql_query = tool_result.get("executed_sql", "")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    # Title
    elements.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    elements.append(Spacer(1, 20))

    # Table
    if results:
        df = pd.DataFrame(results)

        data = [df.columns.tolist()] + df.values.tolist()

        table = Table(data)

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

    # SQL
    elements.append(Paragraph("<b>SQL Query</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))
    elements.append(Preformatted(sql_query, styles["Code"]))

    doc.build(elements)

    buffer.seek(0)
    return buffer