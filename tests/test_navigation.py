import pytest
from hub.navigation import require_observed_navigation
from hub.errors import ObservationError

def test_navigation_rejects_invented_article_and_site_substitution():
    goal='Read https://news.example.test/ and save an article'
    require_observed_navigation(goal,'https://news.example.test/',[])
    for url in ('https://other.test/','https://news.example.test/guessed-article'):
        with pytest.raises(ObservationError):require_observed_navigation(goal,url,[])

def test_navigation_follows_real_links_including_cross_domain():
    actions=[{'tool':'browser_observe','result':{'url':'https://news.example.test/','elements':[{'href':'https://sports.example.test/item/123'}]}}]
    require_observed_navigation('Read https://news.example.test/','https://sports.example.test/item/123',actions)
    with pytest.raises(ObservationError):require_observed_navigation('Read https://news.example.test/','https://sports.example.test/item/124',actions)

def test_failed_calls_do_not_authorize_future_navigation():
    actions=[{'tool':'browser_navigate','result':{'error':'failed','url':'https://wrong.test/'}}]
    with pytest.raises(ObservationError):require_observed_navigation('Open https://requested.test/','https://wrong.test/',actions)

def test_named_site_can_start_but_later_paths_require_evidence():
    require_observed_navigation('Open the company site','https://company.test/',[])
    with pytest.raises(ObservationError):require_observed_navigation('Open the company site','https://company.test/login',[{'tool':'browser_observe','result':{'url':'https://company.test/'}}])
