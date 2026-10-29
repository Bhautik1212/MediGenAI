"""Backend tests. Run from the backend folder:   python -m unittest discover -s tests -v

The Hugging Face network call is replaced with a fake response, so these tests
check OUR code (validation, DB, files, error handling) without internet or a token.
They do not prove that the real model produces good images - test that manually.
"""
import io
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from app import create_app  # noqa: E402
from services import generator  # noqa: E402


def png_bytes(color=(120, 120, 120), size=(64, 64)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


class FakeResponse:
    def __init__(self, status=200, content=b"", content_type="image/png", json_body=None):
        self.status_code = status
        self.content = content
        self.headers = {"content-type": content_type}
        self._json = json_body or {}

    def json(self):
        return self._json


class BaseTest(unittest.TestCase):
    mode = "demo"
    extra = {}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        cfg = {
            "TESTING": True,
            "DATABASE_PATH": os.path.join(self.tmp, "t.db"),
            "IMAGE_DIR": os.path.join(self.tmp, "imgs"),
            "GENERATION_MODE": self.mode,
            "RATE_LIMIT_REQUESTS": 1000,
            "BASE_IMAGE_SIZE": 64,
        }
        cfg.update(self.extra)
        self.app = create_app(cfg)
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def post(self, **kw):
        body = {"prompt": "Generate a synthetic brain MRI-style image for teaching.", "category": "brain_mri",
                "style": "scan", "aspect_ratio": "1:1", "num_images": 1}
        body.update(kw)
        return self.client.post("/api/generate", json=body)


class MetaEndpoints(BaseTest):
    def test_health_reports_demo_mode(self):
        r = self.client.get("/api/health").get_json()
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["demo_mode"])
        self.assertIn("not for clinical use", r["disclaimer"])

    def test_categories(self):
        r = self.client.get("/api/categories").get_json()
        self.assertEqual(len(r["categories"]), 5)
        self.assertEqual(r["limits"]["max_images"], 4)
        self.assertIn("16:9", r["aspect_ratios"])


class Validation(BaseTest):
    def test_short_prompt(self):
        r = self.post(prompt="brain")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["error"]["field"], "prompt")

    def test_long_prompt(self):
        self.assertEqual(self.post(prompt="x" * 600).status_code, 400)

    def test_blocked_prompt(self):
        r = self.post(prompt="Create a fake medical record scan of a real patient")
        self.assertEqual(r.status_code, 400)

    def test_bad_category_style_aspect_count(self):
        self.assertEqual(self.post(category="nope").status_code, 400)
        self.assertEqual(self.post(style="nope").status_code, 400)
        self.assertEqual(self.post(aspect_ratio="9:1").status_code, 400)
        self.assertEqual(self.post(num_images=0).status_code, 400)
        self.assertEqual(self.post(num_images=5).status_code, 400)
        self.assertEqual(self.post(num_images="2").status_code, 400)

    def test_invalid_json(self):
        r = self.client.post("/api/generate", data="not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_rate_limit(self):
        self.app.config["RATE_LIMIT_REQUESTS"] = 2
        from routes import api as api_mod
        api_mod._hits.clear()
        codes = [self.post().status_code for _ in range(3)]
        self.assertEqual(codes, [201, 201, 429])


class DemoFlow(BaseTest):
    def test_generate_history_download_delete(self):
        r = self.post(num_images=2, aspect_ratio="4:3")
        self.assertEqual(r.status_code, 201)
        imgs = r.get_json()["images"]
        self.assertEqual(len(imgs), 2)
        first = imgs[0]
        self.assertTrue(first["is_demo"])
        self.assertEqual(first["provider"], "demo")
        self.assertEqual((first["width"], first["height"]), (64, 48))

        # file exists and is served
        self.assertTrue(os.path.isfile(os.path.join(self.app.config["IMAGE_DIR"], first["filename"])))
        served = self.client.get(first["image_url"])
        self.assertEqual(served.status_code, 200)
        Image.open(io.BytesIO(served.data)).verify()
        served.close()

        # history
        h = self.client.get("/api/history").get_json()
        self.assertEqual(h["total"], 2)
        self.assertEqual(h["items"][0]["id"], imgs[1]["id"])  # newest first
        self.assertEqual(self.client.get("/api/history?category=chest_xray").get_json()["total"], 0)
        self.assertEqual(self.client.get(f"/api/history/{first['id']}").get_json()["prompt"], first["prompt"])

        # download carries the disclaimer strip (image is taller than original)
        d = self.client.get(first["download_url"])
        self.assertEqual(d.status_code, 200)
        self.assertIn("attachment", d.headers["Content-Disposition"])
        dl = Image.open(io.BytesIO(d.data))
        self.assertGreater(dl.height, first["height"])
        d.close()

        # delete removes row and file
        self.assertEqual(self.client.delete(f"/api/history/{first['id']}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/history/{first['id']}").status_code, 404)
        self.assertFalse(os.path.exists(os.path.join(self.app.config["IMAGE_DIR"], first["filename"])))
        self.assertEqual(self.client.delete(f"/api/history/{first['id']}").status_code, 404)

    def test_path_traversal_blocked(self):
        r = self.client.get("/api/images/../t.db")
        self.assertIn(r.status_code, (400, 404))


class HuggingFaceProvider(BaseTest):
    mode = "huggingface"
    extra = {"HF_API_TOKEN": "hf_fake_token", "HF_MODEL_LOADING_RETRIES": 1}

    def test_success_is_stored_as_real_provider(self):
        with mock.patch("services.generator.requests.post", return_value=FakeResponse(200, png_bytes())) as post:
            r = self.post()
        self.assertEqual(r.status_code, 201)
        img = r.get_json()["images"][0]
        self.assertEqual(img["provider"], "huggingface")
        self.assertFalse(img["is_demo"])
        self.assertIn("stable-diffusion", img["model_name"])
        sent = post.call_args.kwargs["json"]
        self.assertIn("synthetic brain MRI", sent["inputs"])
        self.assertIn("grayscale", sent["inputs"])  # style suffix was added
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer hf_fake_token")

    def test_token_never_in_response(self):
        with mock.patch("services.generator.requests.post", return_value=FakeResponse(200, png_bytes())):
            body = self.post().get_data(as_text=True)
        self.assertNotIn("hf_fake_token", body)

    def test_timeout(self):
        import requests
        with mock.patch("services.generator.requests.post", side_effect=requests.exceptions.Timeout()):
            r = self.post()
        self.assertEqual(r.status_code, 504)
        self.assertEqual(r.get_json()["error"]["code"], "timeout")
        self.assertEqual(self.client.get("/api/history").get_json()["total"], 0)

    def test_unreachable(self):
        import requests
        with mock.patch("services.generator.requests.post", side_effect=requests.exceptions.ConnectionError()):
            self.assertEqual(self.post().status_code, 503)

    def test_auth_quota_notfound(self):
        for status, expected, code in [(401, 502, "auth"), (429, 429, "quota"), (404, 502, "model_not_found")]:
            with mock.patch("services.generator.requests.post", return_value=FakeResponse(status, b"", "application/json")):
                r = self.post()
            self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (expected, code))

    def test_model_loading_retries_then_succeeds(self):
        loading = FakeResponse(503, b"", "application/json", {"estimated_time": 1})
        ok = FakeResponse(200, png_bytes())
        with mock.patch("services.generator.requests.post", side_effect=[loading, ok]), \
                mock.patch("services.generator.time.sleep") as sleep:
            r = self.post()
        self.assertEqual(r.status_code, 201)
        sleep.assert_called_once()

    def test_corrupt_image(self):
        with mock.patch("services.generator.requests.post", return_value=FakeResponse(200, b"garbage")):
            self.assertEqual(self.post().status_code, 502)


class ComfyUIProvider(BaseTest):
    mode = "comfyui"
    extra = {
        "COMFYUI_API_URL": "http://comfyui:8188",
        "COMFYUI_UNET_NAME": "qwen-image-2.1-UC-Q4_K_M.gguf",
        "COMFYUI_CLIP_NAME": "qwen3vl_8b_int8_convrot.safetensors",
        "COMFYUI_VAE_NAME": "qwen_image_2.1_vae_bf16.safetensors",
        "COMFYUI_STEPS": 25,
        "COMFYUI_TIMEOUT_SECONDS": 1,
        "COMFYUI_POLL_INTERVAL_SECONDS": 0,
    }

    def test_generate_uses_comfyui_workflow_and_saves_image(self):
        prompt_response = FakeResponse(json_body={"prompt_id": "test-prompt"})
        history_response = FakeResponse(json_body={
            "test-prompt": {
                "outputs": {"10": {"images": [{
                    "filename": "generated.png", "subfolder": "", "type": "output"
                }]}}
            }
        })
        image_response = FakeResponse(200, png_bytes())
        with mock.patch("services.generator.requests.post", return_value=prompt_response) as post, \
                mock.patch("services.generator.requests.get",
                           side_effect=[history_response, image_response]) as get:
            response = self.post()

        self.assertEqual(response.status_code, 201)
        image = response.get_json()["images"][0]
        self.assertEqual(image["provider"], "comfyui")
        self.assertEqual(image["model_name"], self.extra["COMFYUI_UNET_NAME"])
        self.assertFalse(image["is_demo"])
        workflow = post.call_args.kwargs["json"]["prompt"]
        self.assertEqual(workflow["1"]["class_type"], "UnetLoaderGGUF")
        self.assertEqual(workflow["1"]["inputs"]["unet_name"], self.extra["COMFYUI_UNET_NAME"])
        self.assertEqual(workflow["2"]["inputs"]["type"], "qwen_image")
        self.assertIn("synthetic brain MRI", workflow["4"]["inputs"]["text"])
        self.assertEqual(workflow["6"]["inputs"]["width"], 64)
        self.assertEqual(workflow["6"]["inputs"]["height"], 64)
        self.assertTrue(get.call_args_list[0].args[0].endswith("/history/test-prompt"))
        self.assertTrue(get.call_args_list[1].args[0].endswith("/view"))

    def test_unreachable_comfyui_does_not_save_generation(self):
        import requests
        with mock.patch(
            "services.generator.requests.post",
            side_effect=requests.exceptions.ConnectionError(),
        ):
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"]["code"], "unreachable")
        self.assertEqual(self.client.get("/api/history").get_json()["total"], 0)


class LocalCPUProvider(BaseTest):
    mode = "local"
    extra = {
        "LOCAL_MODEL_ID": "segmind/tiny-sd",
        "LOCAL_STEPS": 4,
    }

    def test_cpu_pipeline_enables_vae_slicing_on_vae(self):
        class FakeVAE:
            def __init__(self):
                self.slicing_enabled = False

            def enable_slicing(self):
                self.slicing_enabled = True

        class FakePipeline:
            def __init__(self):
                self.vae = FakeVAE()
                self.attention_slicing_enabled = False

            def to(self, _device):
                return self

            def enable_attention_slicing(self):
                self.attention_slicing_enabled = True

        pipeline = FakePipeline()
        with mock.patch("services.generator._pipeline", None), mock.patch(
            "diffusers.AutoPipelineForText2Image.from_pretrained",
            return_value=pipeline,
        ):
            loaded = generator._get_pipeline({
                "LOCAL_MODEL_ID": "segmind/tiny-sd",
            })

        self.assertIs(loaded, pipeline)
        self.assertTrue(pipeline.attention_slicing_enabled)
        self.assertTrue(pipeline.vae.slicing_enabled)

    def test_cpu_model_is_used_and_stored_as_real_generation(self):
        image = Image.new("RGB", (64, 64), (90, 120, 150))
        with mock.patch("services.generator._local_generate_one", return_value=image) as generate:
            response = self.post()

        self.assertEqual(response.status_code, 201)
        saved = response.get_json()["images"][0]
        self.assertEqual(saved["provider"], "local")
        self.assertEqual(saved["model_name"], "segmind/tiny-sd")
        self.assertFalse(saved["is_demo"])
        generate.assert_called_once()
        self.assertEqual(generate.call_args.args[-1]["LOCAL_STEPS"], 4)

    def test_unexpected_local_error_returns_actionable_api_error(self):
        with mock.patch(
            "services.generator._local_generate_one",
            side_effect=RuntimeError("unexpected pipeline failure"),
        ):
            response = self.post()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "local_failed")
        self.assertIn("Check the backend console", response.get_json()["error"]["message"])
        self.assertEqual(self.client.get("/api/history").get_json()["total"], 0)


class AutoFallbackToDemo(BaseTest):
    mode = "auto"
    extra = {"HF_API_TOKEN": "hf_fake_token", "HF_MODEL_LOADING_RETRIES": 1}

    def test_unsupported_hf_model_falls_back_to_demo(self):
        response = FakeResponse(410, b"", "application/json", {"error": "The requested model is deprecated and no longer supported by provider hf-inference"})
        with mock.patch("services.generator.requests.post", return_value=response):
            r = self.post()
        self.assertEqual(r.status_code, 201)
        payload = r.get_json()["images"][0]
        self.assertEqual(payload["provider"], "demo")
        self.assertTrue(payload["is_demo"])


class NotConfigured(BaseTest):
    mode = "huggingface"
    extra = {"HF_API_TOKEN": ""}

    def test_missing_token_gives_clear_error(self):
        r = self.post()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.get_json()["error"]["code"], "not_configured")
        self.assertTrue(self.client.get("/api/health").get_json()["problems"])


class ProviderResolution(unittest.TestCase):
    def test_auto_with_and_without_token(self):
        self.assertEqual(generator.resolve_provider({"GENERATION_MODE": "auto", "HF_API_TOKEN": ""}), "demo")
        self.assertEqual(generator.resolve_provider({"GENERATION_MODE": "auto", "HF_API_TOKEN": "x"}), "huggingface")
        self.assertEqual(generator.resolve_provider({"GENERATION_MODE": "comfyui", "HF_API_TOKEN": "x"}), "comfyui")

    def test_dimensions(self):
        from services.categories import dimensions_for
        self.assertEqual(dimensions_for("16:9", 768), (768, 432))
        self.assertEqual(dimensions_for("3:4", 768), (576, 768))
        self.assertEqual(dimensions_for("1:1", 512), (512, 512))


if __name__ == "__main__":
    unittest.main()
