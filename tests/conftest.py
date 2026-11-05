"""테스트 공통 설정 — app 을 import 하는 순간 실행되는 db.init_db() 가
프로젝트 폴더의 실제 learning.db 를 만들거나 건드리지 않도록 임시 경로를 먼저 지정한다."""

import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="ew-test-"), "learning.db")
