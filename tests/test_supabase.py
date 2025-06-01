from database.supabase_client import save_programs

def test_save():
    response = save_programs("Test Uni", ["Program A", "Program B"])
    assert response.status_code == 201
