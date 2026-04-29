"""
PropCompassAI — Inspection Report AI UI
Add this as a tab or page in frontend/app.py
"""

import streamlit as st
import io
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml_engine'))
from inspection_ai import analyze_inspection_report, generate_negotiation_strategy


def render_inspection_page(user: dict = None):
    """Render the full Inspection Report AI page."""

    st.markdown("""
    <div style='background:linear-gradient(135deg,#1B3A6B,#2D6A4F);
                padding:1.5rem;border-radius:12px;margin-bottom:1.5rem'>
        <h2 style='color:white;margin:0'>🔍 Inspection Report AI</h2>
        <p style='color:#A8D5B5;margin:0.4rem 0 0'>
        Upload your inspection PDF — AI reads every issue, estimates repair costs,
        and builds your negotiation strategy in seconds.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Usage gate ──────────────────────────────────────────────────
    if user is None:
        st.warning("Please log in to use Inspection Report AI.")
        return

    # ── Input form ──────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        property_address = st.text_input(
            "Property Address",
            placeholder="115 Hunston Dr, Holly Springs, NC 27540",
            help="Enter the property address for the report"
        )
    with col2:
        purchase_price = st.number_input(
            "Purchase Price ($)",
            min_value=50000,
            max_value=10000000,
            value=355000,
            step=5000,
            help="Your offer/purchase price"
        )

    uploaded_file = st.file_uploader(
        "Upload Inspection Report (PDF)",
        type=["pdf"],
        help="Upload the home inspection report PDF"
    )

    # ── Analyze button ───────────────────────────────────────────────
    if uploaded_file and st.button(
        "🔍 Analyze Inspection Report",
        type="primary",
        use_container_width=True
    ):
        with st.spinner("Gemini AI is reading your inspection report... this may take 30-60 seconds"):
            pdf_bytes = uploaded_file.read()
            st.session_state["inspection_pdf_bytes"] = pdf_bytes
            result = analyze_inspection_report(pdf_bytes, property_address)

        if result.get("error"):
            st.error(f"Analysis failed: {result['error']}")
            return

        # Save to session state
        st.session_state["inspection_result"]  = result
        st.session_state["inspection_address"] = property_address
        st.session_state["inspection_price"]   = purchase_price

    # ── Show results ─────────────────────────────────────────────────
    if "inspection_result" in st.session_state:
        result   = st.session_state["inspection_result"]
        address  = st.session_state.get("inspection_address", "")
        price    = st.session_state.get("inspection_price", 355000)

        _render_results(result, address, price)


def _render_results(result: dict, address: str, purchase_price: float):
    """Render the inspection analysis results."""

    total_min = result.get("estimated_total_min", 0)
    total_max = result.get("estimated_total_max", 0)
    critical  = result.get("critical_count", 0)
    important = result.get("important_count", 0)
    minor     = result.get("minor_count", 0)
    total     = result.get("total_issues", 0)

    # ── Summary banner ───────────────────────────────────────────────
    summary = result.get("summary", "")
    if summary:
        st.info(f"**AI Summary:** {summary}")

    # ── Key metrics ──────────────────────────────────────────────────
    st.markdown("### 📊 Inspection Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Issues",    total)
    c2.metric("🔴 Critical",     critical,  delta=f"{critical} items",  delta_color="inverse")
    c3.metric("🟡 Important",    important, delta=f"{important} items", delta_color="off")
    c4.metric("🟢 Minor",        minor)
    c5.metric("Est. Repair Cost", f"${total_min:,}–${total_max:,}")

    # ── Cost vs price ────────────────────────────────────────────────
    if total_max > 0:
        pct = (total_max / purchase_price) * 100
        st.markdown(f"""
        <div style='background:rgba(245,158,11,0.15);border-left:4px solid #F59E0B;
                    padding:0.8rem 1rem;border-radius:8px;margin:1rem 0;'>
            <span style='color:#F1F5F9 !important;font-size:14px;'>
            <strong style='color:#F5C842;'>💡 Cost Context:</strong> Estimated repairs of
            <strong style='color:#F5C842;'>${total_min:,}–${total_max:,}</strong> represent
            <strong style='color:#F5C842;'>{pct:.1f}%</strong>
            <span style='color:#CBD5E1;'> of the ${purchase_price:,.0f} purchase price.
            {'⚠️ Consider requesting a price reduction or repair credit!' if pct > 1 else '✅ Minor repairs relative to purchase price.'}
            </span></span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Issues by category ───────────────────────────────────────────
    issues = result.get("issues", [])

    for category, emoji, color in [
        ("Critical",  "🔴", "#F13A30"),
        ("Important", "🟡", "#F59E0B"),
        ("Minor",     "🟢", "#10B981"),
    ]:
        cat_issues = [i for i in issues if i.get("category") == category]
        if not cat_issues:
            continue

        st.markdown(f"### {emoji} {category} Issues ({len(cat_issues)})")

        for i, issue in enumerate(cat_issues):
            with st.expander(
                f"{issue.get('system','General')} — {issue.get('description','')[:80]}... "
                f"| Est. ${issue.get('cost_min',0):,}–${issue.get('cost_max',0):,}",
                expanded=(category == "Critical")
            ):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Description:** {issue.get('description','')}")
                    st.markdown(f"**Location:** {issue.get('location','Not specified')}")
                    if issue.get("notes"):
                        st.markdown(f"**Why it matters:** {issue.get('notes','')}")
                with col2:
                    st.markdown(f"""
                    <div style='background:rgba(13,22,45,0.8);border:2px solid {color};padding:0.8rem;border-radius:8px;text-align:center'>
                        <div style='font-size:1.2rem;font-weight:700;color:{color}'>
                            ${issue.get('cost_min',0):,}–${issue.get('cost_max',0):,}
                        </div>
                        <div style='font-size:0.8rem;color:#CBD5E1'>Estimated repair cost</div>
                        <div style='font-size:0.75rem;margin-top:0.3rem;font-weight:500'>
                            <span style='color:#CBD5E1'>{issue.get('priority','Repair recommended')}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)


    st.divider()
    # ── Repair Request Email Generator ───────────────────────────────
    st.markdown("### 📧 Repair Request Email Generator")

    col1, col2, col3 = st.columns(3)
    with col1:
        agent_name = st.text_input(
            "Seller Agent Name",
            placeholder="e.g. Chad Smith"
        )
    with col2:
        closing_date = st.text_input(
            "Closing Date",
            placeholder="e.g. May 21, 2026"
        )
    with col3:
        response_by = st.text_input(
            "Response Needed By",
            placeholder="e.g. May 10, 2026"
        )

    if st.button("📧 Generate Repair Request Email",
                 use_container_width=True):
        if not agent_name:
            st.warning("Please enter seller agent name!")
        else:
            # Build critical issues list
            critical_issues  = [i for i in issues
                                 if i.get("category") == "Critical"]
            important_issues = [i for i in issues
                                 if i.get("category") == "Important"]

            critical_text = ""
            if critical_issues:
                critical_text = "\n\nCRITICAL ITEMS — Must be addressed before closing:\n"
                for idx, issue in enumerate(critical_issues, 1):
                    critical_text += f"\n{idx}. {issue.get('system','')} — {issue.get('description','')}"
                    critical_text += f"\n   Location: {issue.get('location','')}"

            important_text = ""
            if important_issues:
                important_text = "\n\nIMPORTANT ITEMS — Please address prior to closing:\n"
                for idx, issue in enumerate(important_issues, 1):
                    important_text += f"\n{idx}. {issue.get('system','')} — {issue.get('description','')}"
                    important_text += f"\n   Location: {issue.get('location','')}"

            closing_line = f"our {closing_date} closing" if closing_date else "our closing date"
            response_line = f"\n\nPlease let us know the seller's response by {response_by} so we can keep {closing_line} on track." if response_by else f"\n\nPlease let us know the seller's response at your earliest convenience so we can keep {closing_line} on track."

            email_body = f"""Hi {agent_name},

Hope you are doing well! We have completed the home inspection for {address or 'the property'}.

Please find the full inspection report attached. We kindly request that the seller review and address the following items prior to closing:{critical_text}{important_text}

Please note that minor cosmetic items are documented in the full inspection report for transparency, but we are not requesting action on those items at this time.{response_line}

Thank you {agent_name}!

Best regards,

Ulaganathan Esakki
NC Licensed Realtor
732-983-7793
e.ulaganathan@gmail.com"""

            st.session_state["repair_email"] = email_body

    if "repair_email" in st.session_state:
        st.markdown("#### ✉️ Repair Request Email — Ready to Send")
        st.info("📎 Remember to attach the full inspection PDF from your licensed inspector!")

        # Display email
        # Display email
        st.markdown(f"""
        <div style='background:#0D1B35;border:1px solid rgba(99,130,255,0.2);
                    border-radius:10px;padding:20px;font-family:monospace;
                    font-size:13px;line-height:1.8;color:#E2E8F0;
                    white-space:pre-wrap;word-wrap:break-word;'>
{st.session_state["repair_email"]}
        </div>
        """, unsafe_allow_html=True)

        # Copy button
        st.markdown(f"""
        <a href="mailto:?subject=Home Inspection Repair Request — {address}&body={st.session_state['repair_email'].replace(chr(10), '%0A').replace(' ', '%20')}"
           target="_blank"
           style='display:inline-block;background:linear-gradient(135deg,#0D6EFD,#1a7fff);
                  color:white;padding:10px 24px;border-radius:100px;
                  text-decoration:none;font-weight:700;font-size:14px;
                  margin-top:8px;'>
            📧 Open in Email Client →
        </a>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Amendment Info Section ────────────────────────────────
        st.markdown("### 📄 Amendment to Contract — Price Reduction")
        st.markdown("""
        <div style='background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);
                    border-left:4px solid #F59E0B;border-radius:10px;padding:14px 16px;'>
            <div style='font-weight:700;color:#F59E0B;margin-bottom:8px;'>
                ⚠️ Compliance Notice
            </div>
            <div style='color:#CBD5E1;font-size:13px;line-height:1.6;'>
                Amendment to Contract must use the official NAR/NCREC standard form.
                Use the information below to fill in the official form manually.
                <br><br>
                <strong style='color:#F1F5F9;'>Do NOT use AI-generated documents as legal contracts.</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📋 Amendment Details — Copy to Official Form")

        col1, col2 = st.columns(2)
        with col1:
            orig_price = st.number_input(
                "Original Purchase Price ($)",
                value=int(purchase_price),
                step=1000
            )
            reduction  = st.number_input(
                "Price Reduction Amount ($)",
                value=0,
                step=500,
                help="Enter actual contractor quotes total"
            )
        with col2:
            new_price = orig_price - reduction
            st.markdown(f"""
            <div style='background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);
                        border-radius:10px;padding:16px;margin-top:24px;text-align:center'>
                <div style='color:#94A3B8;font-size:12px;margin-bottom:4px;'>NEW PURCHASE PRICE</div>
                <div style='font-size:2rem;font-weight:800;color:#10B981;
                            font-family:Space Grotesk,sans-serif;'>
                    ${new_price:,.0f}
                </div>
                <div style='color:#94A3B8;font-size:11px;margin-top:4px;'>
                    Reduction: ${reduction:,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)

        if reduction > 0:
            refused_issues = [i for i in issues
                              if i.get("category") in ["Critical","Important"]]
            st.markdown("#### 📝 Amendment Key Information")
            st.markdown(f"""
            <div style='background:rgba(16,28,52,0.8);border:1px solid rgba(99,130,255,0.2);
                        border-radius:10px;padding:16px;font-family:monospace;font-size:13px;
                        line-height:2;color:#CBD5E1;'>
                <div style='color:#F5C842;font-weight:700;margin-bottom:8px;
                            font-size:14px;letter-spacing:2px;'>
                    ⚠️ DRAFT — FOR REFERENCE ONLY — DO NOT USE AS LEGAL DOCUMENT
                </div>
                <b>Property:</b> {address}<br>
                <b>Original Purchase Price:</b> ${orig_price:,.0f}<br>
                <b>Price Reduction:</b> ${reduction:,.0f}<br>
                <b>New Purchase Price:</b> ${new_price:,.0f}<br>
                <b>Reason:</b> Buyer inspection repair requests — seller agreed to price reduction in lieu of repairs<br>
                <b>Items covered:</b> {len(refused_issues)} inspection items per attached report<br>
                <b>All other terms</b> remain the same as original contract<br>
                <br>
                <div style='color:#F5C842;font-size:11px;'>
                    Copy this information to the official NCREC Amendment to Contract form.
                    Have both parties sign the official form. This is for reference only.
                </div>
            </div>
            """, unsafe_allow_html=True)
    # ── Negotiation recommendation ───────────────────────────────────
    st.markdown("### 🤝 Negotiation Recommendation")
    rec = result.get("negotiation_recommendation", "")
    if rec:
        st.success(rec)

    # ── Generate full strategy button ────────────────────────────────
    if st.button("�� Generate Full Negotiation Strategy",
                 use_container_width=True):
        # Check cache first
        try:
            from inspection_cache import get_cached_strategy, save_strategy_to_cache
            pdf_bytes = st.session_state.get("inspection_pdf_bytes", b"")
            cached_strategy = get_cached_strategy(pdf_bytes, address)
            if cached_strategy:
                st.session_state["negotiation_strategy"] = cached_strategy
                st.success("⚡ Loaded from cache instantly!")
            else:
                with st.spinner("Building your negotiation strategy..."):
                    strategy = generate_negotiation_strategy(
                        result, purchase_price, address)
                    st.session_state["negotiation_strategy"] = strategy
                    # Save to cache
                    save_strategy_to_cache(pdf_bytes, address, strategy)
        except Exception as e:
            with st.spinner("Building your negotiation strategy..."):
                strategy = generate_negotiation_strategy(
                    result, purchase_price, address)
                st.session_state["negotiation_strategy"] = strategy

    if "negotiation_strategy" in st.session_state:
        st.markdown("#### 📋 Full Negotiation Strategy")
        st.markdown(st.session_state["negotiation_strategy"])

    st.divider()

    # ── Cost summary table ───────────────────────────────────────────
    st.markdown("### 💰 Repair Cost Summary")
    import pandas as pd
    rows = []
    for issue in issues:
        rows.append({
            "Category": issue.get("category", ""),
            "System":   issue.get("system", ""),
            "Issue":    issue.get("description", "")[:60] + "...",
            "Min ($)":  issue.get("cost_min", 0),
            "Max ($)":  issue.get("cost_max", 0),
            "Priority": issue.get("priority", ""),
        })
    if rows:
        df = pd.DataFrame(rows)
        df["Min ($)"] = df["Min ($)"].apply(lambda x: f"${x:,}")
        df["Max ($)"] = df["Max ($)"].apply(lambda x: f"${x:,}")
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Totals ───────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("🔴 Critical Repairs",  f"${sum(i.get('cost_max',0) for i in issues if i.get('category')=='Critical'):,}")
    col2.metric("🟡 Important Repairs", f"${sum(i.get('cost_max',0) for i in issues if i.get('category')=='Important'):,}")
    col3.metric("📊 Total Max Repairs", f"${total_max:,}")

    # ── Download PDF report button ───────────────────────────────────
    st.divider()
    st.markdown("### 📄 Download Report")

    if st.button("📥 Generate PDF Report", use_container_width=True):
        pdf_bytes = _generate_pdf_report(result, address, purchase_price)
        if pdf_bytes:
            st.download_button(
                label="⬇️ Download Inspection Analysis PDF",
                data=pdf_bytes,
                file_name=f"Inspection_Analysis_{address[:20].replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )


def _generate_pdf_report(result: dict, address: str, purchase_price: float) -> bytes:
    """Generate a PDF report of the inspection analysis."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)

        NAVY  = HexColor("#1B3A6B")
        GREEN = HexColor("#2D6A4F")
        RED   = HexColor("#DC2626")
        AMBER = HexColor("#D97706")
        GRNLT = HexColor("#DCFCE7")
        REDLT = HexColor("#FEE2E2")
        AMBLT = HexColor("#FEF3C7")
        GRAY  = HexColor("#F1F5F9")

        styles = getSampleStyleSheet()
        story  = []

        # Title
        title_style = ParagraphStyle('title', parent=styles['Title'],
                                     textColor=white, fontSize=18, alignment=TA_CENTER,
                                     backColor=NAVY, spaceAfter=4, spaceBefore=4,
                                     leftIndent=-54, rightIndent=-54)
        story.append(Paragraph("PROPCOMPASSAI — INSPECTION REPORT ANALYSIS", title_style))
        story.append(Spacer(1, 0.1*inch))

        # Address
        addr_style = ParagraphStyle('addr', parent=styles['Normal'],
                                    textColor=NAVY, fontSize=12, alignment=TA_CENTER,
                                    fontName='Helvetica-Bold', spaceAfter=6)
        story.append(Paragraph(f"Property: {address}", addr_style))
        story.append(Paragraph(f"Purchase Price: ${purchase_price:,.0f}", addr_style))
        story.append(Spacer(1, 0.15*inch))

        # Summary box
        summary = result.get("summary", "")
        if summary:
            sum_data = [[Paragraph(f"<b>AI Summary:</b> {summary}",
                                   ParagraphStyle('s', parent=styles['Normal'],
                                                  fontSize=10, textColor=NAVY))]]
            sum_tbl = Table(sum_data, colWidths=[7*inch])
            sum_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), HexColor("#EFF6FF")),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LINEAFTER', (0,0), (0,-1), 4, NAVY),
            ]))
            story.append(sum_tbl)
            story.append(Spacer(1, 0.15*inch))

        # Overview metrics
        story.append(Paragraph("INSPECTION OVERVIEW",
                                ParagraphStyle('h2', parent=styles['Heading2'],
                                               textColor=NAVY, fontSize=13,
                                               fontName='Helvetica-Bold')))

        overview_data = [
            ['Total Issues', 'Critical 🔴', 'Important 🟡', 'Minor 🟢', 'Est. Repair Cost'],
            [str(result.get('total_issues',0)),
             str(result.get('critical_count',0)),
             str(result.get('important_count',0)),
             str(result.get('minor_count',0)),
             f"${result.get('estimated_total_min',0):,}–${result.get('estimated_total_max',0):,}"]
        ]
        ov_tbl = Table(overview_data, colWidths=[1.2*inch, 1.2*inch, 1.3*inch, 1.1*inch, 2.2*inch])
        ov_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), NAVY),
            ('TEXTCOLOR', (0,0), (-1,0), white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,1), (-1,1), GRAY),
            ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,1), (-1,1), 12),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(ov_tbl)
        story.append(Spacer(1, 0.2*inch))

        # Issues table
        issues = result.get("issues", [])
        if issues:
            story.append(Paragraph("DETAILED ISSUES",
                                    ParagraphStyle('h2', parent=styles['Heading2'],
                                                   textColor=NAVY, fontSize=13,
                                                   fontName='Helvetica-Bold')))

            tbl_data = [['Category', 'System', 'Description', 'Location', 'Est. Cost']]
            tbl_colors = []
            for i, issue in enumerate(issues):
                cat = issue.get('category','')
                bg = REDLT if cat=='Critical' else AMBLT if cat=='Important' else GRNLT
                tbl_colors.append(('BACKGROUND', (0, i+1), (-1, i+1), bg))
                cost = f"${issue.get('cost_min',0):,}–${issue.get('cost_max',0):,}"
                desc = issue.get('description','')[:50]+'...' if len(issue.get('description',''))>50 else issue.get('description','')
                tbl_data.append([
                    Paragraph(cat, ParagraphStyle('td', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')),
                    Paragraph(issue.get('system','')[:15], ParagraphStyle('td', parent=styles['Normal'], fontSize=8)),
                    Paragraph(desc, ParagraphStyle('td', parent=styles['Normal'], fontSize=8)),
                    Paragraph(issue.get('location','')[:20], ParagraphStyle('td', parent=styles['Normal'], fontSize=8)),
                    Paragraph(cost, ParagraphStyle('td', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')),
                ])

            issues_tbl = Table(tbl_data, colWidths=[0.8*inch, 0.9*inch, 2.8*inch, 1.3*inch, 1.2*inch])
            tbl_style = [
                ('BACKGROUND', (0,0), (-1,0), NAVY),
                ('TEXTCOLOR', (0,0), (-1,0), white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor("#CCCCCC")),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ] + tbl_colors
            issues_tbl.setStyle(TableStyle(tbl_style))
            story.append(issues_tbl)
            story.append(Spacer(1, 0.2*inch))

        # Negotiation
        rec = result.get("negotiation_recommendation","")
        if rec:
            story.append(Paragraph("NEGOTIATION RECOMMENDATION",
                                    ParagraphStyle('h2', parent=styles['Heading2'],
                                                   textColor=NAVY, fontSize=13,
                                                   fontName='Helvetica-Bold')))
            rec_data = [[Paragraph(rec, ParagraphStyle('rec', parent=styles['Normal'],
                                                        fontSize=10, textColor=GREEN))]]
            rec_tbl = Table(rec_data, colWidths=[7*inch])
            rec_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), GRNLT),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LINEAFTER', (0,0), (0,-1), 4, GREEN),
            ]))
            story.append(rec_tbl)
            story.append(Spacer(1, 0.15*inch))

        # Footer
        footer = ParagraphStyle('footer', parent=styles['Normal'],
                                 fontSize=8, textColor=HexColor("#888888"),
                                 alignment=TA_CENTER)
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(
            "Generated by PropCompassAI | propcompassai.streamlit.app | "
            "This report is for informational purposes only. "
            "Always consult a licensed contractor for accurate repair estimates.",
            footer
        ))

        doc.build(story)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None