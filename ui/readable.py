"""Safe, human-readable profile presentation; does not change stored values."""
from html import escape

FIELDS = (
 ('user_id','Mã hồ sơ','text'),
 ('monthly_primary_income','Thu nhập chính / tháng','money'),
 ('monthly_other_income','Thu nhập phụ / tháng','money'),
 ('monthly_essential_expense','Chi phí thiết yếu / tháng','money'),
 ('monthly_discretionary_expense','Chi phí khác / tháng','money'),
 ('monthly_debt_payment','Trả nợ / tháng','money'),
 ('current_savings','Tiết kiệm hiện có','money'),
 ('emergency_fund_reserved','Quỹ dự phòng giữ lại','money'),
 ('goal_name','Mục tiêu','text'),
 ('goal_amount','Số tiền mục tiêu','money'),
 ('goal_horizon_months','Thời hạn','months'),
 ('risk_tolerance','Mức chấp nhận rủi ro','level'),
 ('liquidity_need','Nhu cầu thanh khoản','level'),
 ('expected_income_growth','Tăng trưởng thu nhập kỳ vọng / năm','percent'),
 ('notes','Ghi chú','text'),
)

def profile_summary_html(profile):
    rows=[]
    for key,label,kind in FIELDS:
        value=profile.get(key)
        if value is None or value == '':
            display='Chưa cung cấp'
        elif kind=='money':
            display=f'{value:,.0f}'.replace(',','.')+' ₫'
        elif kind=='percent':
            display=f'{value * 100:g}'.replace('.',',')+'%'
        elif kind=='months':
            display=f'{value} tháng'
        elif kind=='level':
            display={'low':'Thấp','medium':'Trung bình','high':'Cao'}.get(value,str(value))
        else:
            display=str(value)
        rows.append(f'<div class="p09-summary-item"><span>{escape(label)}</span><strong>{escape(display)}</strong></div>')
    return '<section class="p09-profile-summary"><h3>Hồ sơ của bạn</h3><p>Bản nháp · Kiểm tra lại thông tin trước khi mô phỏng.</p><div class="p09-summary-grid">'+''.join(rows)+'</div></section>'
