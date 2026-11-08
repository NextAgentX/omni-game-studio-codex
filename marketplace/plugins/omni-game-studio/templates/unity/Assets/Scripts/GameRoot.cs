using UnityEngine;

/// <summary>
/// 最小可玩原型：点击/触摸移动方块，吃金币加分，30 秒倒计时。
/// 所有对象在代码里创建，不依赖预制体，便于整体替换成正式实现。
/// 挂到空场景里的任意 GameObject 上即可运行。
/// </summary>
public class GameRoot : MonoBehaviour
{
    const float RoundSeconds = 30f;
    const float MoveSpeed = 6.2f;

    float _score;
    float _timeLeft = RoundSeconds;
    bool _running = true;
    Vector3 _target;

    Transform _player;
    Transform _coin;
    Camera _cam;
    float _halfH, _halfW;

    void Start()
    {
        _cam = Camera.main;
        if (_cam == null)
        {
            var go = new GameObject("Main Camera");
            go.tag = "MainCamera";
            _cam = go.AddComponent<Camera>();
        }
        _cam.orthographic = true;
        _cam.orthographicSize = 5f;
        _cam.clearFlags = CameraClearFlags.SolidColor;
        _cam.backgroundColor = new Color(0.071f, 0.067f, 0.122f);

        _halfH = _cam.orthographicSize;
        _halfW = _halfH * _cam.aspect;

        _player = MakeSquare("Player", new Color(0.486f, 0.239f, 0.937f), 0.72f);
        _player.position = Vector3.zero;
        _target = _player.position;

        _coin = MakeSquare("Coin", new Color(0.984f, 0.749f, 0.141f), 0.4f);
        PlaceCoin();
    }

    static Transform MakeSquare(string name, Color color, float scale)
    {
        var go = new GameObject(name);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = WhiteSprite();
        sr.color = color;
        go.transform.localScale = Vector3.one * scale;
        return go.transform;
    }

    static Sprite _white;

    static Sprite WhiteSprite()
    {
        if (_white != null) return _white;
        var tex = new Texture2D(4, 4, TextureFormat.RGBA32, false);
        var px = new Color32[16];
        for (int i = 0; i < px.Length; i++) px[i] = new Color32(255, 255, 255, 255);
        tex.SetPixels32(px);
        tex.filterMode = FilterMode.Bilinear;
        tex.Apply();
        _white = Sprite.Create(tex, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f), 4f);
        return _white;
    }

    void PlaceCoin()
    {
        _coin.position = new Vector3(
            Random.Range(-_halfW + 0.6f, _halfW - 0.6f),
            Random.Range(-_halfH + 1.2f, _halfH - 0.6f),
            0f);
    }

    void Update()
    {
        if (!_running) return;

        if (Input.GetMouseButtonDown(0))
        {
            var p = _cam.ScreenToWorldPoint(Input.mousePosition);
            p.z = 0f;
            _target = p;
        }

        _player.position = Vector3.MoveTowards(_player.position, _target, MoveSpeed * Time.deltaTime);

        if (Vector3.Distance(_player.position, _coin.position) < 0.55f)
        {
            _score += 10f;
            PlaceCoin();
        }

        _timeLeft -= Time.deltaTime;
        if (_timeLeft <= 0f)
        {
            _timeLeft = 0f;
            _running = false;
            Debug.Log($"[Omni] round over — score {_score}");
        }
    }

    void OnGUI()
    {
        var style = new GUIStyle(GUI.skin.label) { fontSize = 28 };
        style.normal.textColor = Color.white;
        GUI.Label(new Rect(24, 16, 300, 40), $"SCORE {_score:0}", style);
        style.normal.textColor = new Color(0.984f, 0.749f, 0.141f);
        GUI.Label(new Rect(Screen.width - 160, 16, 200, 40), $"{_timeLeft:0.0}s", style);

        if (!_running)
        {
            style.normal.textColor = new Color(0.61f, 0.64f, 0.69f);
            GUI.Label(new Rect(24, Screen.height - 48, 500, 40), "round over — press R to restart", style);
        }

        if (!_running && Input.GetKeyDown(KeyCode.R))
        {
            _score = 0f;
            _timeLeft = RoundSeconds;
            _running = true;
            _player.position = Vector3.zero;
            PlaceCoin();
        }
    }
}
