"""Test Selenium de la page d'accueil — SOLUTION Atelier 8 (partie B).

Prérequis : `pip install selenium`, application lancée, Chrome installé (sinon
Selenium Manager le télécharge au premier lancement, avec le pilote chromedriver).
Lancer :   pytest tests/e2e/test_selenium_accueil.py
Voir le navigateur :   SELENIUM_HEADED=1 pytest tests/e2e/test_selenium_accueil.py

Ce qui change par rapport à Playwright : rien n'attend à notre place. Le catalogue est
chargé par un appel réseau après l'affichage de la page : c'est au test de dire ce qu'il
attend, avec `WebDriverWait`. Sans cette attente, un `find_element` lancé avant la fin du
chargement lève `NoSuchElementException` (sur un poste rapide, il passe par chance).

Le module est ignoré (« skipped ») si Selenium n'est pas installé : il ne casse donc pas
`pytest -m e2e` dans un environnement qui n'a que Playwright, comme le workflow de CI.
"""

import os

import pytest

pytest.importorskip("selenium")

from selenium import webdriver  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

pytestmark = pytest.mark.e2e


def css(testid: str) -> tuple[str, str]:
    return By.CSS_SELECTOR, f'[data-testid="{testid}"]'


@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("SELENIUM_HEADED") != "1":
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,800")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        options.add_argument("--no-sandbox")  # Chrome refuse le bac à sable sous root (conteneur, CI)
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


def test_titre_de_la_page(driver, app_url):
    driver.get(app_url)
    assert "MiniShop" in driver.title
    assert driver.find_element(*css("title")).text == "MiniShop"


def test_ajout_d_un_produit_au_panier(driver, app_url):
    driver.get(app_url)
    wait = WebDriverWait(driver, 10)

    # Attente explicite : le bouton n'existe qu'une fois /products chargé.
    wait.until(EC.element_to_be_clickable(css("add-mug"))).click()

    ligne = wait.until(EC.visibility_of_element_located(css("cart-mug")))
    assert ligne.text.endswith("× 1")
    assert driver.find_element(*css("order-btn")).is_enabled()
