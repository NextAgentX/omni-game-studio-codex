extends Node2D
## 最小可玩原型：点击/触摸移动方块，吃金币加分，30 秒倒计时。
## 用途：验证工程可运行、输入可用、UI 可绘制、状态可推进。
## 所有节点在代码里创建，不依赖场景文件里的复杂结构，便于替换成正式实现。

const ROUND_SECONDS := 30.0
const PLAYER_SIZE := 72.0
const COIN_SIZE := 40.0
const MOVE_SPEED := 620.0

var score := 0
var time_left := ROUND_SECONDS
var running := true
var target_pos := Vector2.ZERO

var player: ColorRect
var score_label: Label
var time_label: Label
var hint_label: Label
var coin: ColorRect
var rng := RandomNumberGenerator.new()


func _ready() -> void:
	rng.randomize()
	var vs := get_viewport_rect().size

	var bg := ColorRect.new()
	bg.color = Color("#12111f")
	bg.position = Vector2.ZERO
	bg.size = vs
	add_child(bg)

	player = ColorRect.new()
	player.color = Color("#7C3AED")
	player.size = Vector2(PLAYER_SIZE, PLAYER_SIZE)
	player.position = vs * 0.5 - player.size * 0.5
	add_child(player)
	target_pos = player.position

	coin = ColorRect.new()
	coin.color = Color("#FBBF24")
	coin.size = Vector2(COIN_SIZE, COIN_SIZE)
	add_child(coin)
	_place_coin()

	score_label = _make_label(44, Vector2(28, 24), Color("#FFFFFF"))
	time_label = _make_label(44, Vector2(vs.x - 170, 24), Color("#FBBF24"))
	hint_label = _make_label(26, Vector2(28, vs.y - 56), Color("#9CA3AF"))
	hint_label.text = "click / tap to move"

	_update_labels()


func _make_label(font_size: int, pos: Vector2, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_color_override("font_color", color)
	l.position = pos
	add_child(l)
	return l


func _place_coin() -> void:
	var vs := get_viewport_rect().size
	coin.position = Vector2(
		rng.randf_range(40, vs.x - COIN_SIZE - 40),
		rng.randf_range(140, vs.y - COIN_SIZE - 120)
	)


func _update_labels() -> void:
	score_label.text = "SCORE %d" % score
	time_label.text = "%0.1fs" % max(time_left, 0.0)


func _input(event: InputEvent) -> void:
	if not running:
		return
	if event is InputEventMouseButton and event.pressed:
		target_pos = event.position - player.size * 0.5
	elif event is InputEventScreenTouch and event.pressed:
		target_pos = event.position - player.size * 0.5


func _process(delta: float) -> void:
	if not running:
		return

	player.position = player.position.move_toward(target_pos, MOVE_SPEED * delta)

	var pc := player.position + player.size * 0.5
	var cc := coin.position + coin.size * 0.5
	if pc.distance_to(cc) < (PLAYER_SIZE + COIN_SIZE) * 0.5:
		score += 10
		_place_coin()

	time_left -= delta
	_update_labels()

	if time_left <= 0.0:
		running = false
		hint_label.text = "round over — score %d" % score
