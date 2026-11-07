from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_demo_pages_render():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert app.metric[0].value == "96"

    app.sidebar.radio[0].set_value("Synthetic Dataset").run()
    assert not app.exception
    assert app.metric[0].value == "1"
    assert set(app.dataframe[0].value["season"]) == {2026}

    app.selectbox[0].set_value(2024).run()
    assert not app.exception
    assert set(app.dataframe[0].value["season"]) == {2024}
