from app.parsers.statement_mapping import load_statement_mapping


def test_statement_mapping_loader_reads_template_codes():
    mapping = load_statement_mapping()

    receivable_loan = mapping.get("financial_position", "135")
    retained_prior_loss = mapping.get("financial_position", "421a")
    retained_current_loss = mapping.get("financial_position", "421b")
    cogs = mapping.get("income_statement", "11")
    direct_cash_receipt = mapping.get("cash_flow_direct", "01")
    indirect_profit = mapping.get("cash_flow_indirect", "01")

    assert receivable_loan is not None
    assert receivable_loan.label == "Phải thu về cho vay ngắn hạn"
    assert receivable_loan.parent_code == "130"
    assert receivable_loan.level == 3
    assert retained_prior_loss is not None
    assert retained_prior_loss.parent_code == "421"
    assert retained_current_loss is not None
    assert retained_current_loss.parent_code == "421"
    assert cogs is not None
    assert cogs.label == "Giá vốn hàng bán"
    assert direct_cash_receipt is not None
    assert direct_cash_receipt.label == "Tiền thu từ bán hàng, cung cấp dịch vụ và doanh thu khác"
    assert indirect_profit is not None
    assert indirect_profit.label == "Lợi nhuận trước thuế"
