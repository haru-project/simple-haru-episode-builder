import json
from pathlib import Path
import pytest
from src.services.demo_language import LANGUAGES, apply_language, normalize_language
from src.models.episode import Episode
from src.services.template_service import TemplateService


def test_language_export_preserves_source_and_scripts():
    goal = {'additional_instructions': ['Keep gestures.']}
    source = {'actions': [{'action_type':'HARU_CONVERSATE', 'action_goal':json.dumps(goal)}, {'action_type':'HARU_SPEAK', 'action_content':['Hello']}]}
    result = apply_language(source, 'uk')
    assert result['demo_language'] == 'uk-UA'
    assert json.loads(source['actions'][0]['action_goal']) == goal
    assert result['actions'][1] == source['actions'][1]
    assert json.loads(result['actions'][0]['action_goal'])['additional_instructions'][-1] == LANGUAGES['uk-UA'][1]
    assert apply_language(result, 'uk') == result
    assert len(json.loads(apply_language(result, 'ja')['actions'][0]['action_goal'])['additional_instructions']) == 2
    with pytest.raises(ValueError):
        normalize_language('xx')


def test_localized_templates_roundtrip():
    for locale in LANGUAGES:
        path = Path(__file__).parents[1] / f'data/tasks/templates/MultilingualDemo_{locale}.json'
        template = json.loads(path.read_text())
        assert Episode.from_dict(template).to_dict()['demo_language'] == locale
        assert json.loads(template['actions'][0]['action_goal'])['additional_instructions'] == [LANGUAGES[locale][1]]


def test_demos_are_visible_in_template_picker():
    names = {t.name for t in TemplateService(Path(__file__).parents[1] / 'data/tasks/templates').list_templates()}
    assert {f'MultilingualDemo_{locale}' for locale in LANGUAGES} <= names


def test_sidebar_language_selector(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.delenv('HARU_DEMO_LANGUAGE', raising=False)
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run(timeout=20)
    assert not app.exception
    assert app.sidebar.selectbox[0].value == 'en-US'
    app.sidebar.selectbox[0].set_value('uk-UA').run()
    assert not app.exception
    assert app.sidebar.selectbox[0].value == 'uk-UA'
