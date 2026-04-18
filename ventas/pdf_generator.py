# ventas/pdf_generator.py
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generar_pdf_factura(venta) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    verde = colors.HexColor('#27AE60')
    gris_oscuro = colors.HexColor('#2C3E50')
    gris_claro = colors.HexColor('#F2F3F4')
    styles = getSampleStyleSheet()
    elementos = []

    # Estilos
    def estilo(nombre, size, bold=False, color=colors.black, align=TA_LEFT):
        return ParagraphStyle(nombre, parent=styles['Normal'],
                              fontSize=size, textColor=color,
                              fontName='Helvetica-Bold' if bold else 'Helvetica',
                              alignment=align)

    # ── Encabezado ──────────────────────────────────────────────
    elementos.append(Paragraph("MercaMax", estilo('titulo', 22, bold=True, color=verde)))
    elementos.append(Spacer(1, 0.3*cm))
    elementos.append(HRFlowable(width="100%", thickness=2, color=verde))
    elementos.append(Spacer(1, 0.4*cm))

    # ── Datos de factura ────────────────────────────────────────
    factura = venta.factura
    fecha_str = venta.fecha_hora.strftime('%d/%m/%Y %H:%M')
    metodo_display = dict(venta.METODO_PAGO_CHOICES).get(venta.metodo_pago, venta.metodo_pago)

    datos_enc = [
        ['N° FACTURA', factura.numero_factura, 'FECHA', fecha_str],
        ['CAJERO', venta.cajero.get_full_name() or venta.cajero.username,
         'MÉTODO PAGO', metodo_display],
        ['ESTADO', venta.estado, '', ''],
    ]
    t_enc = Table(datos_enc, colWidths=[3*cm, 6*cm, 3.5*cm, 4.5*cm])
    t_enc.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), gris_oscuro),
        ('TEXTCOLOR', (2, 0), (2, -1), gris_oscuro),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elementos.append(t_enc)
    elementos.append(Spacer(1, 0.4*cm))

    # ── Cliente ─────────────────────────────────────────────────
    cliente = venta.cliente
    if cliente:
        elementos.append(HRFlowable(width="100%", thickness=0.5, color=gris_claro))
        elementos.append(Spacer(1, 0.2*cm))
        elementos.append(Paragraph("DATOS DEL CLIENTE",
                                    estilo('sec', 8, bold=True, color=verde)))
        elementos.append(Spacer(1, 0.2*cm))
        datos_cli = [
            ['Nombre:', cliente.nombre,
             'Documento:', f"{cliente.tipo_documento}: {cliente.numero_documento}"],
        ]
        if cliente.telefono or cliente.email:
            datos_cli.append([
                'Teléfono:', cliente.telefono or '—',
                'Email:', cliente.email or '—'
            ])
        t_cli = Table(datos_cli, colWidths=[2.5*cm, 7*cm, 2.5*cm, 5*cm])
        t_cli.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elementos.append(t_cli)
        elementos.append(Spacer(1, 0.4*cm))

    # ── Tabla de productos ──────────────────────────────────────
    elementos.append(HRFlowable(width="100%", thickness=0.5, color=gris_claro))
    elementos.append(Spacer(1, 0.2*cm))
    elementos.append(Paragraph("DETALLE DE PRODUCTOS",
                                estilo('sec2', 8, bold=True, color=verde)))
    elementos.append(Spacer(1, 0.3*cm))

    filas = [['#', 'Producto', 'Cant.', 'P. Unit.', 'IVA%', 'Impuesto', 'Total Línea']]
    detalles = venta.detalleventa_set.all()
    for i, d in enumerate(detalles, 1):
        filas.append([
            str(i),
            d.stock_item.lote.producto.nombre,
            str(d.cantidad),
            f"${float(d.precio_unitario):,.0f}",
            f"{float(d.porcentaje_iva):.0f}%",
            f"${float(d.impuesto):,.0f}",
            f"${float(d.total_linea):,.0f}",
        ])

    t_prod = Table(filas, colWidths=[0.8*cm, 6.5*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.2*cm, 2.5*cm])
    t_prod.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), verde),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_claro]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elementos.append(t_prod)
    elementos.append(Spacer(1, 0.5*cm))

    # ── Desglose de totales ─────────────────────────────────────
    datos_tot = [
        ['', 'Subtotal (sin impuestos):', f"${float(venta.subtotal):,.0f}"],
        ['', 'Total Impuestos (IVA):', f"${float(venta.total_impuestos):,.0f}"],
        ['', 'TOTAL A PAGAR:', f"${float(venta.total):,.0f}"],
    ]
    t_tot = Table(datos_tot, colWidths=[8.5*cm, 5.5*cm, 3*cm])
    t_tot.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica'),
        ('FONTNAME', (1, 0), (1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 1), 10),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, 2), 13),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 2), (-1, 2), verde),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 2), (-1, 2), 1.5, verde),
    ]))
    elementos.append(t_tot)
    elementos.append(Spacer(1, 1*cm))

    # ── Pie de página ───────────────────────────────────────────
    elementos.append(HRFlowable(width="100%", thickness=1, color=verde))
    elementos.append(Spacer(1, 0.2*cm))
    elementos.append(Paragraph(
        "Gracias por su compra en MercaMax • Este documento es su comprobante de pago",
        estilo('pie', 8, color=colors.grey, align=TA_CENTER)
    ))

    doc.build(elementos)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes