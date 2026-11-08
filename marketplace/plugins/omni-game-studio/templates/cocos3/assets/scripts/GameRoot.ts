import {
    _decorator, Component, Node, Graphics, Label, Color, UITransform,
    input, Input, EventTouch, EventMouse, Vec3, view, Canvas,
} from 'cc';

const { ccclass } = _decorator;

/**
 * 最小可玩原型：点击/触摸移动方块，吃金币加分，30 秒倒计时。
 * 全部节点在代码里创建，不依赖预制体与美术资源，便于整体替换成正式实现。
 *
 * 挂载方式见 SETUP.md：挂在 Canvas 节点上。
 */
@ccclass('GameRoot')
export class GameRoot extends Component {
    private readonly ROUND = 30;
    private readonly MOVE_SPEED = 900;
    private readonly PLAYER = 72;
    private readonly COIN = 40;

    private score = 0;
    private timeLeft = this.ROUND;
    private running = true;

    private player!: Node;
    private coin!: Node;
    private gPlayer!: Graphics;
    private gCoin!: Graphics;
    private lbScore!: Label;
    private lbTime!: Label;
    private lbHint!: Label;

    private target = new Vec3();
    private halfW = 360;
    private halfH = 640;

    onLoad() {
        const size = view.getVisibleSize();
        this.halfW = size.width / 2;
        this.halfH = size.height / 2;

        this.drawBackground();
        this.player = this.makeSquare('Player', this.PLAYER, new Color(124, 58, 237, 255));
        this.gPlayer = this.player.getComponent(Graphics)!;
        this.coin = this.makeSquare('Coin', this.COIN, new Color(251, 191, 36, 255));
        this.gCoin = this.coin.getComponent(Graphics)!;

        this.lbScore = this.makeLabel('SCORE 0', 44, new Vec3(-this.halfW + 28, this.halfH - 60));
        this.lbTime = this.makeLabel(`${this.ROUND.toFixed(1)}s`, 44, new Vec3(this.halfW - 150, this.halfH - 60));
        this.lbHint = this.makeLabel('click / tap to move', 26, new Vec3(-this.halfW + 28, -this.halfH + 40));

        this.placeCoin();

        input.on(Input.EventType.TOUCH_START, this.onTouch, this);
        input.on(Input.EventType.MOUSE_DOWN, this.onMouse, this);
    }

    onDestroy() {
        input.off(Input.EventType.TOUCH_START, this.onTouch, this);
        input.off(Input.EventType.MOUSE_DOWN, this.onMouse, this);
    }

    private drawBackground() {
        const bg = new Node('BG');
        this.node.parent!.addChild(bg);
        bg.setSiblingIndex(0);
        const ut = bg.addComponent(UITransform);
        ut.setContentSize(this.halfW * 2, this.halfH * 2);
        const g = bg.addComponent(Graphics);
        g.fillColor = new Color(18, 17, 31, 255);
        g.rect(-this.halfW, -this.halfH, this.halfW * 2, this.halfH * 2);
        g.fill();
    }

    private makeSquare(name: string, size: number, color: Color): Node {
        const n = new Node(name);
        this.node.addChild(n);
        const ut = n.addComponent(UITransform);
        ut.setContentSize(size, size);
        const g = n.addComponent(Graphics);
        g.fillColor = color;
        g.roundRect(-size / 2, -size / 2, size, size, size / 6);
        g.fill();
        return n;
    }

    private makeLabel(text: string, fontSize: number, pos: Vec3): Label {
        const n = new Node('Label');
        this.node.addChild(n);
        n.setPosition(pos);
        const lb = n.addComponent(Label);
        lb.string = text;
        lb.fontSize = fontSize;
        lb.lineHeight = fontSize * 1.2;
        lb.color = new Color(255, 255, 255, 255);
        lb.horizontalAlign = Label.HorizontalAlign.LEFT;
        return lb;
    }

    private placeCoin() {
        const x = (Math.random() - 0.5) * (this.halfW * 2 - 160);
        const y = (Math.random() - 0.5) * (this.halfH * 2 - 320);
        this.coin.setPosition(x, y, 0);
    }

    private onTouch(e: EventTouch) {
        if (!this.running) return;
        const p = e.getUILocation();
        this.target = new Vec3(p.x - this.halfW, p.y - this.halfH, 0);
    }

    private onMouse(e: EventMouse) {
        if (!this.running) return;
        const p = e.getUILocation();
        this.target = new Vec3(p.x - this.halfW, p.y - this.halfH, 0);
    }

    update(dt: number) {
        if (!this.running) return;

        const cur = this.player.position;
        const next = new Vec3(
            cur.x + Math.sign(this.target.x - cur.x) * Math.min(this.MOVE_SPEED * dt, Math.abs(this.target.x - cur.x)),
            cur.y + Math.sign(this.target.y - cur.y) * Math.min(this.MOVE_SPEED * dt, Math.abs(this.target.y - cur.y)),
            0,
        );
        this.player.setPosition(next);

        const d = Vec3.distance(next, this.coin.position);
        if (d < (this.PLAYER + this.COIN) / 2) {
            this.score += 10;
            this.placeCoin();
        }

        this.timeLeft -= dt;
        if (this.timeLeft <= 0) {
            this.timeLeft = 0;
            this.running = false;
            this.lbHint.string = `round over — score ${this.score}`;
        }
        this.lbScore.string = `SCORE ${this.score}`;
        this.lbTime.string = `${this.timeLeft.toFixed(1)}s`;
    }
}
