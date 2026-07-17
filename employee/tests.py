from django.test import TestCase
from django.urls import reverse


class LandingPageTests(TestCase):
    def test_landing_page_is_available_at_root(self):
        response = self.client.get(reverse("landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LINGARAJ SANITARY")
        self.assertTemplateUsed(response, "landing.html")
