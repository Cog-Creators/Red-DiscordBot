# Downloader's test repo reference

This file can be used as a reference on what repo contains
if some dev will want to add more test in future.

Branch master
---

**Commit:** c950fc05a540dd76b944719c2a3302da2e2f3090
**Commit message:** Initial commit, prepare files.
**Tree status:**
```
downloader_testrepo/
    ├── mycog
A   │   ├── __init__.py
A   ├── sample_file1.txt
A   └── sample_file2.txt
```
---
**Commit:** fb99eb7d2d5bed514efc98fe6686b368f8425745
**Tag:** lightweight
**Commit message:** Add, modify, rename and remove a file.
**Tree status:**
```
downloader_testrepo/
    ├── mycog/
M   │   ├── __init__.py
A   ├── added_file.txt
D   ├── sample_file1.txt
R   └── sample_file2.txt -> sample_file3.txt
```
---
**Commit:** a7120330cc179396914e0d6af80cfa282adc124b
**Tag:** annotated (sha1: 41f6cf3b58e774d2b3414ced3ee9f2541f1c682f)
**Commit message:** Remove mycog.
**Tree status:**
```
downloader_testrepo/
D   ├── mycog/
D   │   ├── __init__.py
    ├── added_file.txt
    └── sample_file3.txt
```
---
**Commit:** 2db662c1d341b1db7d225ccc1af4019ba5228c70
**Commit message:** One commit after mycog removal.
**Tree status:**
```
downloader_testrepo/
    ├── added_file.txt
    ├── sample_file3.txt
A   └── sample_file4.txt
```

Branch with persistent HEAD
---

**Commit:** a0ccc2390883c85a361f5a90c72e1b07958939fa
**Branch:** dont_add_commits
**Commit message:** Don't edit this, this is used for tests for current commit, latest commit, full sha1 from branch name.
**Tree status:**
```
downloader_testrepo/
A   └── sample_file1.txt
```

Branches with ambiguous commits (95da0b57)
---

**Commit:** 95da0b576271cb5bee5f3e075074c03ee05fed05
**Branch:** ambiguous_1
**Commit message:** Ambiguous commit 16955
**Tree status:**
```
downloader_testrepo/
A   └── sample_file1.txt
```


**Commit:** 95da0b57a416d9c8ce950554228d1fc195c30b43
**Branch:** ambiguous_2
**Commit message:** Ambiguous commit 44414
**Tree status:**
```
downloader_testrepo/
A   └── sample_file1.txt
```


Branch with ambiguous tag (c6f0)
---

**Commit:** c6f0e5ec04d99bdf8c6c78ff20d66d286eecb3ea
**Branch:** ambiguous_with_tag
**Tag:** ambiguous_tag_66387 (sha1: c6f028f843389c850e2c20d8dd1f5fa498252764)
**Commit message:** Commit ambiguous with tag.
**Tree status:**

```
downloader_testrepo/
A   └── sample_file1.txt
```