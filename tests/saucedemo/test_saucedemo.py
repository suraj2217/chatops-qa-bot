"""End-to-end UI checks run by /run-tests ui against SauceDemo."""

from __future__ import annotations

import os
import re

from playwright.sync_api import Page, expect


BASE_URL = os.getenv("SAUCEDEMO_BASE_URL", "https://www.saucedemo.com/")
USERNAME = os.getenv("SAUCEDEMO_USERNAME", "standard_user")
PASSWORD = os.getenv("SAUCEDEMO_PASSWORD", "secret_sauce")


def _open_login(page: Page) -> None:
    page.goto(BASE_URL, wait_until="domcontentloaded")


def test_standard_user_can_sign_in(page: Page) -> None:
    _open_login(page)
    page.get_by_placeholder("Username").fill(USERNAME)
    page.get_by_placeholder("Password").fill(PASSWORD)
    page.get_by_role("button", name="Login").click()

    expect(page.get_by_text("Products", exact=True)).to_be_visible()
    expect(page).to_have_url(re.compile(r".*inventory\.html"))


def test_invalid_password_shows_login_error(page: Page) -> None:
    _open_login(page)
    page.get_by_placeholder("Username").fill(USERNAME)
    page.get_by_placeholder("Password").fill("incorrect-password")
    page.get_by_role("button", name="Login").click()

    expect(page.locator('[data-test="error"]')).to_contain_text(
        "Username and password do not match"
    )


def test_user_can_add_a_product_to_the_cart(page: Page) -> None:
    _open_login(page)
    page.get_by_placeholder("Username").fill(USERNAME)
    page.get_by_placeholder("Password").fill(PASSWORD)
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_text("Products", exact=True)).to_be_visible()

    page.get_by_role("button", name="Add to cart").first.click()
    expect(page.locator(".shopping_cart_badge")).to_have_text("1")
    page.locator(".shopping_cart_link").click()
    expect(page.get_by_text("Sauce Labs Backpack", exact=True)).to_be_visible()
