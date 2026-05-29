import pytest
from utils.title_classifier import classify_title


# -------------------------------------------------------------------
# CEO titles
# -------------------------------------------------------------------
class TestCEOClassification:
    def test_ceo_exact(self):
        assert classify_title("CEO") == "CEO"

    def test_ceo_lowercase(self):
        assert classify_title("ceo") == "CEO"

    def test_chief_executive_officer(self):
        assert classify_title("Chief Executive Officer") == "CEO"

    def test_founder(self):
        assert classify_title("Founder") == "CEO"

    def test_co_founder(self):
        assert classify_title("Co-Founder & CEO") == "CEO"

    def test_president(self):
        assert classify_title("President") == "CEO"

    def test_owner(self):
        assert classify_title("Owner") == "CEO"

    def test_managing_director(self):
        assert classify_title("Managing Director") == "CEO"


# -------------------------------------------------------------------
# CTO titles
# -------------------------------------------------------------------
class TestCTOClassification:
    def test_cto_exact(self):
        assert classify_title("CTO") == "CTO"

    def test_chief_technology_officer(self):
        assert classify_title("Chief Technology Officer") == "CTO"

    def test_chief_product_officer(self):
        assert classify_title("Chief Product Officer") == "CTO"

    def test_cpo_abbreviation(self):
        assert classify_title("CPO") == "CTO"

    def test_chief_architect(self):
        assert classify_title("Chief Architect") == "CTO"

    def test_vp_engineering(self):
        assert classify_title("VP of Engineering") == "CTO"

    def test_vice_president_technology(self):
        assert classify_title("Vice President of Technology") == "CTO"

    def test_head_of_data(self):
        assert classify_title("Head of Data") == "CTO"

    def test_director_of_software(self):
        assert classify_title("Director of Software") == "CTO"

    def test_director_of_infrastructure(self):
        assert classify_title("Director of Infrastructure") == "CTO"


# -------------------------------------------------------------------
# CFO titles
# -------------------------------------------------------------------
class TestCFOClassification:
    def test_cfo_exact(self):
        assert classify_title("CFO") == "CFO"

    def test_chief_financial_officer(self):
        assert classify_title("Chief Financial Officer") == "CFO"

    def test_treasurer(self):
        assert classify_title("Treasurer") == "CFO"

    def test_controller(self):
        assert classify_title("Controller") == "CFO"

    def test_finance_director(self):
        assert classify_title("Finance Director") == "CFO"

    def test_finance_manager(self):
        assert classify_title("Finance Manager") == "CFO"

    def test_head_of_finance(self):
        assert classify_title("Head of Finance") == "CFO"


# -------------------------------------------------------------------
# Manager titles
# -------------------------------------------------------------------
class TestManagerClassification:
    def test_engineering_manager(self):
        assert classify_title("Engineering Manager") == "Manager"

    def test_product_manager(self):
        assert classify_title("Product Manager") == "Manager"

    def test_project_manager(self):
        assert classify_title("Project Manager") == "Manager"

    def test_scrum_master(self):
        assert classify_title("Scrum Master") == "Manager"

    def test_team_lead(self):
        assert classify_title("Team Lead") == "Manager"

    def test_supervisor(self):
        assert classify_title("Supervisor") == "Manager"

    def test_coordinator(self):
        assert classify_title("Operations Coordinator") == "Manager"


# -------------------------------------------------------------------
# General / Fallback titles
# -------------------------------------------------------------------
class TestGeneralClassification:
    def test_none_title(self):
        assert classify_title(None) == "General"

    def test_empty_string(self):
        assert classify_title("") == "General"

    def test_software_engineer(self):
        assert classify_title("Staff Software Engineer") == "General"

    def test_data_analyst(self):
        assert classify_title("Data Analyst") == "General"

    def test_marketing_specialist(self):
        assert classify_title("Marketing Specialist") == "General"

    def test_hr_coordinator(self):
        # "coordinator" → Manager bucket
        assert classify_title("HR Coordinator") == "Manager"

    def test_unknown_title(self):
        assert classify_title("Astronaut") == "General"
