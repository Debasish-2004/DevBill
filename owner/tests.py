from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from owner.models import Category, Product
from owner.views import compress_image_for_upload


class ImageCompressionTests(TestCase):
    def test_compress_image_for_upload_reduces_size_to_target(self):
        image = Image.new('RGB', (2000, 2000), color=(255, 0, 0))
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)

        uploaded = SimpleUploadedFile(
            'large.jpg',
            buffer.getvalue(),
            content_type='image/jpeg',
        )

        compressed = compress_image_for_upload(uploaded, max_size_bytes=500 * 1024)
        compressed_bytes = compressed.read()

        self.assertLessEqual(len(compressed_bytes), 500 * 1024)


class OwnerSearchTests(TestCase):
    def test_owner_search_returns_edit_links_for_matching_products(self):
        User = get_user_model()
        User.objects.create_user(
            username='owner',
            password='secret123',
            is_active=True,
            is_staff=False,
        )
        category = Category.objects.create(name='Sanitary', has_subcategories=False)
        product = Product.objects.create(
            name='Premium Soap',
            category=category,
            place='Shelf A',
            minimum_selling_price=10,
            current_price=15,
        )

        self.client.login(username='owner', password='secret123')
        response = self.client.get(reverse('owner_search_products'), {'q': 'soap'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['url'], reverse('edit_product', args=[product.id]))
