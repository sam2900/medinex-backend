import unittest

from src.schemas import (
    Table3VisitDetails,
    Table3VisitRow,
    Table4ProcedureDetails,
    Table4ProcedureRow,
)
from src.table5_non_procedures import extract_table5_non_procedures


def _row_map(table5):
    return {item.code: item for item in table5.items if item.code}


class Table5NonProcedureTests(unittest.TestCase):
    def test_assigns_rules_across_visit_types(self):
        table3 = Table3VisitDetails(
            pdf_name="protocol.pdf",
            visits=[
                Table3VisitRow(visit_title="Screening Visit", visit_id="SCR"),
                Table3VisitRow(visit_title="Baseline", visit_id="BL"),
                Table3VisitRow(visit_title="Week 4", visit_id="W4"),
                Table3VisitRow(visit_title="Telephone Follow-up", visit_id="TEL"),
                Table3VisitRow(visit_title="End of Treatment", visit_id="EOT"),
            ],
        )

        table4 = Table4ProcedureDetails(
            pdf_name="protocol.pdf",
            visit_columns=["SCR", "BL", "W4", "TEL", "EOT"],
            procedures=[
                Table4ProcedureRow(
                    procedure="Informed Consent",
                    visit_values={"SCR": "X", "BL": "", "W4": "", "TEL": "", "EOT": ""},
                ),
                Table4ProcedureRow(
                    procedure="Administration of Study Treatment",
                    visit_values={"SCR": "", "BL": "X", "W4": "", "TEL": "", "EOT": ""},
                ),
                Table4ProcedureRow(
                    procedure="Vital Signs",
                    visit_values={"SCR": "", "BL": "X", "W4": "X", "TEL": "", "EOT": "X"},
                ),
            ],
        )

        table5 = extract_table5_non_procedures(
            pdf_name="protocol.pdf",
            table3=table3,
            table4=table4,
        )
        rows = _row_map(table5)

        self.assertEqual(rows["INT-NP-002"].visit_values["SCR"], "3.0")
        self.assertEqual(rows["INT-NP-004"].visit_values["SCR"], "2.0")
        self.assertEqual(rows["INT-NP-026"].visit_values["SCR"], "1.5")

        self.assertEqual(rows["INT-NP-002"].visit_values["BL"], "3.0")
        self.assertEqual(rows["INT-NP-004"].visit_values["BL"], "2.0")
        self.assertEqual(rows["INT-NP-026"].visit_values["BL"], "1.5")

        self.assertEqual(rows["INT-NP-001"].visit_values["W4"], "2.0")
        self.assertEqual(rows["INT-NP-003"].visit_values["W4"], "1.0")
        self.assertEqual(rows["INT-NP-026"].visit_values["W4"], "1.0")

        self.assertEqual(rows["INT-NP-001"].visit_values["TEL"], "0.5")
        self.assertEqual(rows["INT-NP-026"].visit_values["TEL"], "0.5")
        self.assertEqual(rows["INT-NP-003"].visit_values["TEL"], "")

        self.assertEqual(rows["INT-NP-002"].visit_values["EOT"], "3.0")
        self.assertEqual(rows["INT-NP-004"].visit_values["EOT"], "2.0")
        self.assertEqual(rows["INT-NP-026"].visit_values["EOT"], "1.5")

        self.assertIn("INT-NP-033", rows)
        self.assertEqual(rows["INT-NP-033"].visit_values["BL"], "1.0")

    def test_interim_visit_becomes_complex_when_more_than_seven_procedures(self):
        table3 = Table3VisitDetails(
            pdf_name="protocol.pdf",
            visits=[
                Table3VisitRow(visit_title="Screening", visit_id="SCR"),
                Table3VisitRow(visit_title="Week 8", visit_id="W8"),
            ],
        )

        procedures = [
            Table4ProcedureRow(
                procedure=f"Procedure {idx}",
                visit_values={"SCR": "", "W8": "X"},
            )
            for idx in range(8)
        ]
        table4 = Table4ProcedureDetails(
            pdf_name="protocol.pdf",
            visit_columns=["SCR", "W8"],
            procedures=procedures,
        )

        table5 = extract_table5_non_procedures(
            pdf_name="protocol.pdf",
            table3=table3,
            table4=table4,
        )
        rows = _row_map(table5)

        self.assertEqual(rows["INT-NP-001"].visit_values["W8"], "3.0")
        self.assertEqual(rows["INT-NP-003"].visit_values["W8"], "1.5")
        self.assertEqual(rows["INT-NP-026"].visit_values["W8"], "1.0")

    def test_conditional_ip_dispensing_row_is_omitted_without_trigger(self):
        table3 = Table3VisitDetails(
            pdf_name="protocol.pdf",
            visits=[Table3VisitRow(visit_title="Screening", visit_id="SCR")],
        )
        table4 = Table4ProcedureDetails(
            pdf_name="protocol.pdf",
            visit_columns=["SCR"],
            procedures=[
                Table4ProcedureRow(
                    procedure="Informed Consent",
                    visit_values={"SCR": "X"},
                )
            ],
        )

        table5 = extract_table5_non_procedures(
            pdf_name="protocol.pdf",
            table3=table3,
            table4=table4,
        )
        rows = _row_map(table5)

        self.assertNotIn("INT-NP-033", rows)


if __name__ == "__main__":
    unittest.main()
