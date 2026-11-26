"""Preserve legacy chat data and refresh the bundled runtime on Android upgrades."""

from pathlib import Path


def replace_once(path, original, replacement):
    source = path.read_text(encoding="utf-8")
    if source.count(replacement) == 1 and original not in source:
        return
    if source.count(original) != 1 or replacement in source:
        raise RuntimeError(f"The Android bootstrap changed in {path}. Review its upgrade behavior.")
    path.write_text(source.replace(original, replacement, 1), encoding="utf-8")


def before_apk_build(_toolchain):
    java = Path("src/main/java/org/kivy/android")
    replace_once(
        java / "PythonActivity.java",
        'PythonUtil.unpackAsset(mActivity, "private", app_root_file, true);',
        'PythonUtil.unpackAsset(mActivity, "private", app_root_file, false);',
    )
    # The two archives share a destination. Only _python_bundle belongs entirely
    # to the interpreter. Old native extensions can shadow new Python modules.
    replace_once(
        java / "PythonUtil.java",
        """            AssetExtract ae = new AssetExtract(ctx);
            if (!ae.extractTar(resource + ".so", target.getAbsolutePath(), "pybundle")) {
                String msg = "Could not extract " + resource + " data.";
                if (ctx instanceof Activity) {
                    toastError((Activity)ctx, msg);
                } else {
                    Log.v(TAG, msg);
                }
            }""",
        """            File runtime = new File(target, "_python_bundle");
            if (runtime.exists()) {
                recursiveDelete(runtime);
            }
            AssetExtract ae = new AssetExtract(ctx);
            if (!ae.extractTar(resource + ".so", target.getAbsolutePath(), "pybundle")) {
                String msg = "Could not extract " + resource + " data.";
                if (ctx instanceof Activity) {
                    toastError((Activity)ctx, msg);
                } else {
                    Log.v(TAG, msg);
                }
                return;
            }""",
    )
