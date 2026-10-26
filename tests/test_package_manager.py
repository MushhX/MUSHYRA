import zipfile

import pytest

import mux_lang.package_manager as package_manager


def test_package_names_reject_windows_device_names():
    with pytest.raises(ValueError):
        package_manager._validate_name("CON")


def test_semver_prerelease_order_and_zero_major_caret_range():
    assert package_manager._version_sort_key("1.0.0-alpha.10") > package_manager._version_sort_key("1.0.0-alpha.2")
    assert package_manager._version_satisfies("0.2.9", "^0.2.0")
    assert not package_manager._version_satisfies("0.3.0", "^0.2.0")
    assert not package_manager._version_satisfies("1.0.0-alpha.2", ">=1.0.0-alpha.10")


def test_signed_file_map_must_match_payload():
    expected = {"main.mux": "a" * 64}
    assert package_manager._verify_manifest_file_map(expected, expected) == expected
    with pytest.raises(ValueError, match="no coinciden"):
        package_manager._verify_manifest_file_map(expected, {"main.mux": "b" * 64})


def test_package_archive_is_sorted_and_hashable(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "main.mux").write_text('print("ok")\n', encoding="utf-8")
    (package / "mux-package.json").write_text(
        '{"name":"hello","version":"1.0.0","main":"main.mux"}', encoding="utf-8"
    )
    archive = tmp_path / "dist" / "hello.zip"
    digest = package_manager.create_package_archive(package, archive)
    assert len(digest) == 64
    assert package_manager._sha256(archive) == digest
    assert package_manager.create_package_archive(package, archive) == digest


def test_zip_extractor_rejects_parent_traversal(tmp_path):
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.mux", "print(1)")
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(ValueError, match="Ruta no segura"):
            package_manager._safe_extract(archive, tmp_path / "extract")


def test_local_package_install_and_uninstall_are_reversible(tmp_path, monkeypatch):
    home = tmp_path / "mux-home"
    monkeypatch.setattr(package_manager, "MUX_HOME", home)
    monkeypatch.setattr(package_manager, "PACKAGES_DIR", home / "packages")
    monkeypatch.setattr(package_manager, "REGISTRY_FILE", home / "registry.json")
    monkeypatch.setattr(package_manager, "LOCK_FILE", home / "registry.lock")
    package = tmp_path / "hello"
    package.mkdir()
    (package / "mux-package.json").write_text(
        '{"name":"hello","version":"1.0.0","main":"main.mux"}', encoding="utf-8"
    )
    (package / "main.mux").write_text('print("hello")\n', encoding="utf-8")
    metadata = package_manager.install_package(str(package))
    assert metadata["version"] == "1.0.0"
    assert (home / "packages" / "hello" / "hello.mux").is_file()
    assert package_manager.uninstall_package("hello") is True
    assert not (home / "packages" / "hello").exists()
