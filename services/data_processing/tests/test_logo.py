from data_processing.logo import logo_filename


def test_logo_filename_slugifies_team_name():
    assert logo_filename("ER-Force") == "er-force.png"
    assert logo_filename("TIGERs Mannheim") == "tigers-mannheim.png"


def test_logo_filename_replaces_all_spaces():
    assert logo_filename("UBC Thunderbots") == "ubc-thunderbots.png"
    assert logo_filename("A B C") == "a-b-c.png"
