"""Engine must apply per-model runtime profiles, not just save them."""
import ast
from pathlib import Path


def test_engine_dispatch_resolves_model_profile_before_context_packet():
    tree = ast.parse(Path("hub/engine.py").read_text(encoding="utf-8"))
    engine = next(node for node in tree.body
                  if isinstance(node, ast.ClassDef) and node.name == "Engine")
    chat = next(node for node in engine.body
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "chat")
    text = ast.unparse(chat)
    assert "effective_inference" in text, "Engine.chat ignores model-specific memory/context policy"
    assert "model_inference_options" in text, "GPU/CPU allocation not propagated to backend options"
    assert "coding_model" in text, "Configured coding model is ignored for code tasks"
    assert text.index("effective_inference") < text.index("build_adaptive_packet")
    assert "model_profile_diagnostic" in text
