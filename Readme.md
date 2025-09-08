# 프롬프트는 전부 prompts.py에 있습니다. 이걸 깎으시면 됨

# pick_best_thought(thoughts: List[Any], evals: List[Any], threshold: float = 3)의 float = 를 바꾸시면 threshold 설정 가능

# 입력 파라미터는 자유롭게 수정하시면 됩니다.


# 처음 실행할 때 설정 (터미널에)
cd delivery
python3 -m venv myenv
source myenv1/bin/activate
pip install -r requirements.txt

# 실행할 때
cd delivery
source myenv1/bin/activate
python agents.py

python -m venv myenv
.\myenv1\Scripts\Activate.ps1
pip install -r requirements.txt.