import sys
sys.path.insert(0, ".")
from app.database.connection import db
from decimal import Decimal
from app.services.reminder_snapshot_service import reminder_snapshot_service

mc = 2713
start = "04/01/2024"
end = "03/31/2025"

q1 = f"SELECT t1.VchType, t2.Value1, t2.MasterCode1, t2.MasterCode2 FROM Tran2 t2 INNER JOIN Tran1 t1 ON t1.VchCode = t2.VchCode WHERE t2.RecType = 1 AND (t2.MasterCode1 = {mc} OR t2.MasterCode2 = {mc}) AND t1.Date >= #{start}# AND t1.Date <= #{end}#"

print(f"--- Raw Transactions for Party {mc} ---")
orig_bal = Decimal("0")

mc1_opt = Decimal("0")
mc2_opt = Decimal("0")

with db.get_cursor(company_id="default") as c:
    c.execute(q1)
    for r in c.fetchall():
        vtype = r[0]
        v1 = reminder_snapshot_service._to_decimal(r[1])
        mc1 = r[2]
        mc2 = r[3]
        
        # Original logic
        party_code = mc1 if mc1 == mc else (mc2 if mc2 == mc else 0)
        orig_cont = reminder_snapshot_service._signed_contribution(vtype, v1)
        orig_bal += orig_cont
        
        print(f"VchType: {vtype:2d} | Val1: {v1:10s} | MC1: {mc1} MC2: {mc2} | OrigContrib: {orig_cont:10s}")

        # Opt logic simulation
        # For MC1 grouped query:
        if mc1 == mc:
            abs_v = abs(v1)
            mc1_opt += reminder_snapshot_service._signed_contribution(vtype, abs_v)

        # For MC2 grouped query:
        if mc2 == mc:
            abs_v = abs(v1)
            mc2_opt += reminder_snapshot_service._signed_contribution(vtype, abs_v)

print(f"Totals -> Orig: {orig_bal}, Opt (MC1+MC2): {mc1_opt + mc2_opt}")
