"""Keep pre-v46 user data until Python can migrate it out of the app bundle."""

from pathlib import Path


def before_apk_build(_toolchain):
    # python-for-android calls this from the Gradle distribution directory.
    activity = Path("src/main/java/org/kivy/android/PythonActivity.java")
    source = activity.read_text(encoding="utf-8")
    original = 'PythonUtil.unpackAsset(mActivity, "private", app_root_file, true);'
    preserved = 'PythonUtil.unpackAsset(mActivity, "private", app_root_file, false);'
    if source.count(preserved) == 1 and original not in source:
        return
    if source.count(original) != 1 or preserved in source:
        raise RuntimeError("The Android bootstrap changed its asset update code. Check data migration before building.")
    activity.write_text(source.replace(original, preserved, 1), encoding="utf-8")
