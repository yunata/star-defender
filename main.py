import pyxel
import random
import math

class StarDefender:
    def __init__(self):
        # ゲーム画面の初期化 - モバイル向けに最適化
        pyxel.init(160, 140, title="スターデフェンダー", fps=30, display_scale=4)
        pyxel.load("assets.pyxres")  # スプライトとサウンドをロード
        pyxel.mouse(False)  # マウスカーソルを非表示に変更
        
        # パフォーマンス最適化用の変数
        self.skip_frame = 0
        self.max_enemies = 8  # さらに敵の数を削減
        self.max_particles = 10  # パーティクル数も削減
        self.max_shots = 15  # 同時に表示する弾の数を制限
        
        self.scene = "TITLE"
        self.is_paused = False
        self.reset_game()
        
        # タッチ操作用の変数
        self.touch_last_x = 0
        self.touch_last_y = 0
        self.touch_fire_timer = 0
        self.touch_start_time = 0
        self.is_tap = False
        
        # モバイル状態検出
        self.is_mobile = False
        try:
            # Webブラウザ実行時のモバイル判定を試みる
            import platform
            self.is_mobile = "mobile" in platform.platform().lower() or "android" in platform.platform().lower() or "ios" in platform.platform().lower()
        except:
            pass
        
        # ゲーム開始
        pyxel.run(self.update, self.draw)
    
    def reset_game(self):
        # プレイヤー情報
        self.player = {
            'x': 80,
            'y': 100,
            'width': 8,
            'height': 8,
            'lives': 3,
            'invincible': 0,
            'power_level': 0,
            'shield': 0
        }
        
        # ゲーム状態
        self.shots = []
        self.enemies = []
        self.powerups = []
        self.explosions = []
        self.stars = []
        self.boss = None
        self.boss_gauge = 0
        self.boss_gauge_max = 1000
        self.boss_appeared = False
        
        # 背景色の設定
        self.bg_color = 0  # 最初の背景は黒
        
        # ステージ情報
        self.score = 0
        self.stage = 1
        self.enemy_spawn_timer = 0
        
        # 背景の星を生成（さらに削減）
        for i in range(15):  # 20から15に削減
            self.stars.append({
                'x': pyxel.rndi(0, 159),
                'y': pyxel.rndi(0, 119),
                'speed': pyxel.rndf(0.5, 1.5),
                'color': pyxel.rndi(5, 7)
            })
        
        # タッチ操作フラグ
        self.is_touching = False
    
    def update(self):
        # フレームスキップカウンターを更新
        self.skip_frame += 1
        
        # ゲームパッドの処理はシンプルに保つ
        # 一時停止切り替え（ESCキーまたはポーズボタン）
        if (pyxel.btnp(pyxel.KEY_ESCAPE) or 
            (hasattr(pyxel, 'GAMEPAD1_BUTTON_START') and pyxel.btnp(pyxel.GAMEPAD1_BUTTON_START))):
            if self.scene == "GAME":
                self.is_paused = not self.is_paused
                if self.is_paused:
                    pyxel.stop()
                else:
                    pyxel.playm(0, loop=True)
        
        # シーンごとの更新処理
        if self.scene == "TITLE":
            self.update_title()
        elif self.scene == "GAME":
            if not self.is_paused:
                self.update_game()
        elif self.scene == "GAMEOVER":
            self.update_gameover()
        
        # リスタート処理
        if pyxel.btnp(pyxel.KEY_R):
            self.reset_game()
            self.scene = "GAME"
            self.is_paused = False
    
    def update_title(self):
        # スタート画面の更新処理
        start_pressed = pyxel.btnp(pyxel.KEY_SPACE)
        
        # ゲームパッドのAボタン（存在する場合のみ）
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_A') and pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A):
            start_pressed = True
        
        # タップ判定
        if self.is_tap:
            start_pressed = True
        
        if start_pressed:
            self.scene = "GAME"
            self.is_paused = False
            pyxel.playm(0, loop=True)
            self.is_tap = False
    
    def update_game(self):
        # プレイヤーの更新
        self.update_player()
        
        # モバイル用タッチコントロールの更新
        self.update_touch_controls()
        
        # ショットの更新（数を制限）
        if len(self.shots) <= self.max_shots:
            self.update_shots()
        else:
            # 弾が多すぎる場合は古い弾を削除
            self.shots = self.shots[-self.max_shots:]
        
        # 敵の更新
        self.update_enemies()
        
        # パワーアップアイテムの更新
        self.update_powerups()
        
        # エフェクトの更新
        self.update_explosions()
        
        # 星の更新は4フレームに1回だけ行う（さらに軽量化）
        if self.skip_frame % 4 == 0:
            self.update_stars()
        
        # 敵の生成タイミング管理
        self.enemy_spawn_timer -= 1
        if self.enemy_spawn_timer <= 0 and len(self.enemies) < self.max_enemies:
            self.spawn_enemy()
            # 出現間隔をさらに長く
            self.enemy_spawn_timer = 100 - min(60, self.stage * 8)  # ステージに応じて出現間隔を短縮
        
        # ボス出現条件をゲージベースに変更
        if not self.boss_appeared and self.boss_gauge >= self.boss_gauge_max:
            self.boss_appeared = True # ボス出現フラグを立てる
            
            # 強力な敵として生成（より強力に）
            strong_enemy = {
                'x': random.randint(20, 140),
                'y': random.randint(-40, -30),
                'width': 16,
                'height': 16,
                'type': 'boss',  # ボス用の新しいタイプ
                'health': 10 + self.stage * 2,  # 耐久力をさらに上げる
                'score': 500, # 高得点
                'speed': 0.4,
                'fire_rate': 0.1, # 発射確率が非常に高い
                'move_x': random.choice([-0.8, 0.8]),
                'fire_pattern': 'spread',  # 特殊な攻撃パターン
                'next_fire': 30,  # 次の発射までのカウンター
                'anim_frame': 0,  # アニメーションフレーム
                'anim_counter': 0  # アニメーションカウンター
            }
            self.enemies.append(strong_enemy)
            # ボス出現音
            pyxel.play(0, 3)
            
            # ボス出現時に必ずパワーアップアイテムも出現させる
            self.powerups.append({
                'x': random.randint(10, 150),
                'y': random.randint(-20, -10),
                'width': 8,
                'height': 8,
                'type': random.choice(['power', 'shield']),
                'speed': 1
            })
    
    def update_gameover(self):
        # ゲームオーバー画面の更新処理
        restart_pressed = pyxel.btnp(pyxel.KEY_R)
        
        # ゲームパッドのAボタン（存在する場合のみ）
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_A') and pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A):
            restart_pressed = True
        
        # タップ判定
        if self.is_tap:
            restart_pressed = True
        
        if restart_pressed:
            self.reset_game()
            self.scene = "GAME"
            self.is_paused = False
    
    def update_player(self):
        # 無敵時間と盾の更新
        if self.player['invincible'] > 0:
            self.player['invincible'] -= 1
        if self.player['shield'] > 0:
            self.player['shield'] -= 1
        
        # 移動速度
        speed = 2
        
        # キーボード入力による移動
        move_left = pyxel.btn(pyxel.KEY_LEFT)
        move_right = pyxel.btn(pyxel.KEY_RIGHT)
        move_up = pyxel.btn(pyxel.KEY_UP)
        move_down = pyxel.btn(pyxel.KEY_DOWN)
        
        # ゲームパッド入力（存在する場合のみ）
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_DPAD_LEFT'):
            move_left = move_left or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
            move_right = move_right or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
            move_up = move_up or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_UP)
            move_down = move_down or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN)
        
        # 移動処理
        if move_left:
            self.player['x'] = max(self.player['x'] - speed, 0)
        if move_right:
            self.player['x'] = min(self.player['x'] + speed, 160 - self.player['width'])
        if move_up:
            self.player['y'] = max(self.player['y'] - speed, 0)
        if move_down:
            self.player['y'] = min(self.player['y'] + speed, 120 - self.player['height'])
        
        # ショット発射（キーボード）
        fire_pressed = pyxel.btnp(pyxel.KEY_SPACE, 12, 4)
        
        # ゲームパッドのショットボタン（存在する場合のみ）
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_A'):
            fire_pressed = fire_pressed or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A, 12, 4)
        
        if fire_pressed:
            self.fire_player_shot()
        
        # タッチ操作による移動（タッチ画面用）
        if self.is_touching:
            # 移動と射撃の処理
            self.touch_fire_timer += 1
            if self.touch_fire_timer >= 8:  # 射撃間隔を少し長く
                self.fire_player_shot()
                self.touch_fire_timer = 0
    
    def update_touch_controls(self):
        # タッチ状態をリセット
        self.is_touching = False
        self.is_tap = False
        
        # タッチ操作の検出
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.touch_last_x = pyxel.mouse_x
            self.touch_last_y = pyxel.mouse_y
            self.touch_start_time = pyxel.frame_count
        
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            x, y = pyxel.mouse_x, pyxel.mouse_y
            
            # 短時間タップ判定
            if pyxel.frame_count - self.touch_start_time < 5:
                self.is_tap = True
            
            # タイトル/ゲームオーバー画面のタップ判定
            if self.scene == "TITLE" or self.scene == "GAMEOVER":
                if 20 <= x <= 140 and 30 <= y <= 110:
                    self.is_tap = True
            
            # ゲーム中のタッチ操作
            if self.scene == "GAME":
                self.is_touching = True
                
                # タッチ位置に自機を移動（単純な実装）
                target_x = x - self.player['width'] // 2
                target_y = y - self.player['height'] // 2
                
                # 移動速度制限
                max_move = 4
                dx = target_x - self.player['x']
                dy = target_y - self.player['y']
                
                if abs(dx) > max_move:
                    dx = max_move * (1 if dx > 0 else -1)
                if abs(dy) > max_move:
                    dy = max_move * (1 if dy > 0 else -1)
                
                # プレイヤーを移動
                self.player['x'] = max(min(self.player['x'] + dx, 160 - self.player['width']), 0)
                self.player['y'] = max(min(self.player['y'] + dy, 120 - self.player['height']), 0)
        
        # タッチ終了時の処理
        if not pyxel.btn(pyxel.MOUSE_BUTTON_LEFT) and self.is_touching:
            self.is_touching = False
            self.touch_fire_timer = 0
    
    def fire_player_shot(self):
        # プレイヤーの弾発射関数
        power = self.player['power_level']
        
        # ショット音
        pyxel.play(0, 0)
        
        # パワーレベルに応じた弾の生成
        if power == 0:
            # 基本ショット
            self.shots.append({
                'x': self.player['x'] + 4,
                'y': self.player['y'] - 4,
                'width': 2,
                'height': 4,
                'type': 'player',
                'damage': 1,
                'speed': 4
            })
        elif power == 1:
            # ダブルショット
            self.shots.append({
                'x': self.player['x'] + 1,
                'y': self.player['y'],
                'width': 2,
                'height': 4,
                'type': 'player',
                'damage': 1,
                'speed': 4
            })
            self.shots.append({
                'x': self.player['x'] + 5,
                'y': self.player['y'],
                'width': 2,
                'height': 4,
                'type': 'player',
                'damage': 1,
                'speed': 4
            })
        else:
            # トリプルショット (3方向)
            shot_speed_y = 3.5  # Spread shot vertical speed
            shot_speed_x = 1.0  # Spread shot horizontal speed
            self.shots.append({
                'x': self.player['x'] + 3, # Center
                'y': self.player['y'] - 4,
                'width': 2,
                'height': 4,
                'type': 'player',
                'damage': 1,
                'speed': shot_speed_y, # Vertical speed
                'dx': 0 # Horizontal speed
            })
            self.shots.append({
                'x': self.player['x'] + 1, # Left
                'y': self.player['y'] - 2,
                'width': 2,
                'height': 4,
                'type': 'player',
                'damage': 1,
                'speed': shot_speed_y,
                'dx': -shot_speed_x
            })
            self.shots.append({
                'x': self.player['x'] + 5, # Right
                'y': self.player['y'] - 2,
                'width': 2,
                'height': 4,
                'type': 'player',
                'damage': 1,
                'speed': shot_speed_y,
                'dx': shot_speed_x
            })
    
    def update_shots(self):
        # ショットの更新
        for shot in list(self.shots):
            # ショットのタイプに応じた移動
            if shot['type'] == 'player':
                shot['y'] -= shot['speed']
                # 横方向の移動がある場合 (パワーアップ用)
                if 'dx' in shot:
                    shot['x'] += shot['dx']
                # 画面外に出たショットを削除
                if shot['y'] < -shot['height'] or shot['x'] < 0 or shot['x'] > 160:
                    if shot in self.shots: # Avoid error if removed by collision check
                        self.shots.remove(shot)
            elif shot['type'] == 'enemy':
                shot['y'] += shot['speed']
                
                # 横方向の移動がある場合
                if 'dx' in shot:
                    shot['x'] += shot['dx']
                
                # 敵の弾とプレイヤーの衝突判定
                if not self.player['invincible'] > 0 and self.check_collision(shot, self.player):
                    if self.player['shield'] > 0:
                        # シールドがある場合はダメージなし
                        self.shots.remove(shot)
                        # シールド効果音
                        pyxel.play(0, 3)
                    else:
                        # シールドがなければライフ減少
                        self.player['lives'] -= 1
                        self.player['invincible'] = 60  # 1秒間の無敵
                        self.create_explosion(self.player['x'], self.player['y'])
                        self.shots.remove(shot)
                        pyxel.play(0, 2)  # ダメージ音
                        
                        if self.player['lives'] <= 0:
                            self.scene = "GAMEOVER"
                            self.is_paused = False
                    continue
                
                # 画面外に出たショットを削除
                if shot['y'] > 140 or shot['x'] < 0 or shot['x'] > 160:
                    if shot in self.shots: # Avoid error if removed by collision check
                         self.shots.remove(shot)
    
    def update_enemies(self):
        # 敵の更新
        for enemy in list(self.enemies):
            # 敵の移動
            enemy['y'] += enemy['speed']
            
            # 左右の動きがある敵
            if 'move_x' in enemy and enemy['move_x'] != 0:
                enemy['x'] += enemy['move_x']
                # 画面端での向きの反転
                if enemy['x'] <= 0 or enemy['x'] >= 160 - enemy['width']:
                    enemy['move_x'] = -enemy['move_x']
            
            # ボスのアニメーション更新
            if enemy['type'] == 'boss' and 'anim_counter' in enemy:
                enemy['anim_counter'] += 1
                if enemy['anim_counter'] >= 10:  # 10フレームごとにアニメーション
                    enemy['anim_counter'] = 0
                    enemy['anim_frame'] = (enemy['anim_frame'] + 1) % 2
            
            # 通常敵の弾発射
            if 'fire_rate' in enemy and random.random() < enemy['fire_rate']:
                if len(self.shots) < self.max_shots:  # 弾数制限のチェック
                    # ボスの場合は特殊な攻撃パターン
                    if enemy['type'] == 'boss' and 'fire_pattern' in enemy:
                        if enemy['fire_pattern'] == 'spread':
                            # 次の発射までのカウンターを減少
                            if 'next_fire' in enemy:
                                enemy['next_fire'] -= 1
                                
                                # カウンターが0になったら発射
                                if enemy['next_fire'] <= 0:
                                    # 散弾パターン (3発同時に異なる角度で発射)
                                    for i in range(3):
                                        angle = -1 + i  # -1, 0, 1の角度（左、中央、右）
                                        self.shots.append({
                                            'x': enemy['x'] + enemy['width'] // 2 + angle * 4,
                                            'y': enemy['y'] + enemy['height'],
                                            'width': 2,
                                            'height': 4,
                                            'type': 'enemy',
                                            'damage': 1,
                                            'speed': 2.5,
                                            'dx': angle * 0.5  # 水平方向への移動
                                        })
                                    
                                    # 次の発射までのカウンターをリセット
                                    enemy['next_fire'] = 25  # 攻撃間隔を短くする
                    else:
                        # 通常の敵の弾発射
                        self.shots.append({
                            'x': enemy['x'] + enemy['width'] // 2,
                            'y': enemy['y'] + enemy['height'],
                            'width': 2,
                            'height': 4,
                            'type': 'enemy',
                            'damage': 1,
                            'speed': 2
                        })
            
            # 画面外に出た敵を削除
            if enemy['y'] > 140:
                self.enemies.remove(enemy)
                continue
            
            # プレイヤーとの衝突判定
            if (not self.player['invincible'] > 0 and
                self.check_collision(enemy, self.player)):
                if self.player['shield'] > 0:
                    # シールドがある場合はダメージなし、敵を破壊
                    self.create_explosion(enemy['x'], enemy['y'])
                    self.enemies.remove(enemy)
                    self.add_score(enemy['score'])
                    
                    # 敵撃破時にボスゲージを加算 (ボス自身は加算しない)
                    if enemy['type'] != 'boss':
                        gauge_increase = 0
                        if enemy['type'] == 'small':
                            gauge_increase = 20 # 小さい敵のゲージ上昇量 (調整可能)
                        elif enemy['type'] == 'medium':
                            gauge_increase = 50 # 中くらいの敵のゲージ上昇量 (調整可能)
                        
                        if not self.boss_appeared: # ボス出現前のみゲージを加算
                            self.boss_gauge = min(self.boss_gauge + gauge_increase, self.boss_gauge_max)
                else:
                    # シールドがなければライフ減少
                    self.player['lives'] -= 1
                    self.player['invincible'] = 60  # 1秒間の無敵
                    self.create_explosion(self.player['x'], self.player['y'])
                    pyxel.play(0, 2)  # ダメージ音
                    
                    if self.player['lives'] <= 0:
                        self.scene = "GAMEOVER"
                        self.is_paused = False
                continue
            
            # プレイヤーの弾との衝突判定
            for shot in list(self.shots):
                if shot['type'] == 'player' and self.check_collision(shot, enemy):
                    # 敵にダメージ
                    enemy['health'] -= shot['damage']
                    self.shots.remove(shot)
                    
                    # 敵の体力が0以下になったら破壊
                    if enemy['health'] <= 0:
                        self.create_explosion(enemy['x'], enemy['y'])
                        
                        # ボスの場合は大きな爆発
                        if enemy['type'] == 'boss':
                            # 追加の爆発エフェクト
                            for i in range(5):
                                x = enemy['x'] + random.uniform(0, enemy['width'])
                                y = enemy['y'] + random.uniform(0, enemy['height'])
                                self.create_explosion(x, y)
                            
                            # ボスを倒したらステージアップと背景色変更
                            self.stage += 1
                            self.boss_appeared = False  # 次のボス出現のためにフラグをリセット
                            self.boss_gauge = 0  # ボスゲージもリセット
                            
                            # 背景色を変更（ステージごとに少しずつ変化）
                            self.bg_color = (self.stage - 1) % 5  # 0, 1, 2, 3, 4 の循環
                        
                        # パワーアップアイテムのドロップ（確率、ボスは確定でドロップ）
                        drop_chance = 0.1  # 通常敵のドロップ率
                        if enemy['type'] == 'boss':
                            drop_chance = 1.0  # ボスは確定ドロップ
                            
                        if random.random() < drop_chance:
                            self.powerups.append({
                                'x': enemy['x'] + enemy['width'] // 2,
                                'y': enemy['y'] + enemy['height'] // 2,
                                'width': 8,
                                'height': 8,
                                'type': random.choice(['power', 'shield']),
                                'speed': 1
                            })
                        
                        # スコア加算
                        self.add_score(enemy['score'])
                        # 敵撃破時にボスゲージを加算 (ボス自身は加算しない)
                        if enemy['type'] != 'boss':
                            gauge_increase = 0
                            if enemy['type'] == 'small':
                                gauge_increase = 20 # 小さい敵のゲージ上昇量 (調整可能)
                            elif enemy['type'] == 'medium':
                                gauge_increase = 50 # 中くらいの敵のゲージ上昇量 (調整可能)
                            
                            if not self.boss_appeared: # ボス出現前のみゲージを加算
                                self.boss_gauge = min(self.boss_gauge + gauge_increase, self.boss_gauge_max)
                        
                        self.enemies.remove(enemy)
                    break
    
    def update_powerups(self):
        # パワーアップアイテムの更新
        for powerup in list(self.powerups):
            powerup['y'] += powerup['speed']
            
            # 画面外に出たアイテムを削除
            if powerup['y'] > 140:
                self.powerups.remove(powerup)
                continue
            
            # プレイヤーとの衝突判定
            if self.check_collision(powerup, self.player):
                # パワーアップ効果
                if powerup['type'] == 'power':
                    self.player['power_level'] = min(2, self.player['power_level'] + 1)
                elif powerup['type'] == 'shield':
                    self.player['shield'] = 300  # シールド効果（10秒）
                
                # アイテム取得音
                pyxel.play(0, 3)
                
                self.powerups.remove(powerup)
    
    def update_explosions(self):
        # 爆発エフェクトの更新
        for exp in list(self.explosions):
            exp['radius'] += exp['speed']
            exp['life'] -= 1
            if exp['life'] <= 0:
                self.explosions.remove(exp)
    
    def update_stars(self):
        # 星の更新
        for star in self.stars:
            star['y'] += star['speed']
            if star['y'] > 139:
                star['y'] = 0
                star['x'] = random.randint(0, 159)
    
    def spawn_enemy(self):
        # 敵の生成（タイプを最小限にして最適化）
        enemy_type = random.choice(['small', 'medium'])
        
        # ステージに応じた敵の強化
        stage_factor = min(self.stage * 0.15, 1.0)  # ステージが上がるほど強くなる
        
        if enemy_type == 'small':
            enemy = {
                'x': random.randint(0, 152),
                'y': random.randint(-20, -10),
                'width': 8,
                'height': 8,
                'type': 'small',
                'health': 1,
                'score': 10,
                'speed': random.uniform(0.8, 2.0) * (1 + stage_factor),  # 速度を上げる
                'fire_rate': 0.005 + (stage_factor * 0.01)  # ステージが上がると発射確率も上がる
            }
        else:
            enemy = {
                'x': random.randint(10, 142),
                'y': random.randint(-30, -20),
                'width': 16,
                'height': 16,
                'type': 'medium',
                'health': 2,
                'score': 50,
                'speed': random.uniform(0.5, 1.2) * (1 + stage_factor),  # 速度を上げる
                'fire_rate': 0.015 + (stage_factor * 0.02),  # 発射確率を上げる
                'move_x': random.choice([-0.8, 0.8]) * (1 + stage_factor * 0.5)  # 左右移動も速く
            }
        
        # パワーアップ出現率の増加
        drop_rate = random.random()
        if drop_rate < 0.03 + (stage_factor * 0.01):  # 低確率でパワーアップアイテムを直接生成
            self.powerups.append({
                'x': random.randint(10, 150),
                'y': random.randint(-20, -10),
                'width': 8,
                'height': 8,
                'type': random.choice(['power', 'shield']),
                'speed': 1
            })
        
        self.enemies.append(enemy)
    
    def create_explosion(self, x, y):
        # 爆発エフェクトの生成
        colors = [8, 9, 10, 11]
        
        # エフェクト数を制限
        if len(self.explosions) < self.max_particles:
            for i in range(3):  # 爆発の粒子数を3に制限
                self.explosions.append({
                    'x': x + random.uniform(-5, 5),
                    'y': y + random.uniform(-5, 5),
                    'radius': random.uniform(1, 3),
                    'speed': random.uniform(0.2, 0.8),
                    'life': random.randint(10, 20),
                    'color': random.choice(colors)
                })
        
        # 爆発音
        pyxel.play(0, 1)
    
    def add_score(self, value):
        # スコア加算
        self.score += value
        
        # スコアに応じたステージアップ
        if self.score > 0 and self.score % 1000 == 0:
            self.stage += 1
    
    def draw(self):
        # 画面をクリア (背景色をステージに応じて変更)
        pyxel.cls(self.bg_color)
        
        # 星（背景）の描画
        self.draw_stars()
        
        # シーンに応じた描画処理
        if self.scene == "TITLE":
            self.draw_title()
        elif self.scene == "GAME":
            self.draw_game()
            
            # 一時停止画面の描画
            if self.is_paused:
                self.draw_pause_screen()
                
        elif self.scene == "GAMEOVER":
            self.draw_gameover()
    
    def draw_stars(self):
        # 背景の星を描画
        for star in self.stars:
            pyxel.pset(star['x'], star['y'], star['color'])
    
    def draw_title(self):
        # タイトル画面の描画
        pyxel.text(55, 40, "STAR DEFENDER", 7)
        pyxel.text(50, 60, "PRESS SPACE TO START", 11)
        
        # モバイル用テキスト
        if self.is_mobile:
            pyxel.text(60, 70, "OR TAP TO START", 11)
        
        # ゲームパッド用のテキスト
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_A'):
            pyxel.text(50, 80, "OR PRESS A TO START", 11)
        
        # コントロール説明
        pyxel.text(30, 100, "ARROW KEYS: MOVE", 6)
        pyxel.text(30, 110, "SPACE: FIRE", 6)
    
    def draw_game(self):
        # 敵と弾の描画
        for enemy in self.enemies:
            # 敵の種類に応じたスプライト描画
            if enemy['type'] == 'small':
                u, v = 8, 0
            elif enemy['type'] == 'medium':
                u, v = 0, 16
            elif enemy['type'] == 'boss':  # ボス用の描画設定
                # ボスのアニメーション（2フレーム交互）
                if 'anim_frame' in enemy and enemy['anim_frame'] == 1:
                    u, v = 32, 16  # 2フレーム目
                else:
                    u, v = 16, 16  # 1フレーム目
            else:
                u, v = 0, 0
                
            w = enemy['width']
            h = enemy['height']
            pyxel.blt(enemy['x'], enemy['y'], 0, u, v, w, h, 0)
            
            # ボスの場合は体力ゲージと輪郭を表示
            if enemy['type'] == 'boss':
                # 体力ゲージの背景
                pyxel.rect(enemy['x'], enemy['y'] - 4, enemy['width'], 2, 1)
                # 現在の体力を表示（初期値は10+stage*2なので、それを100%として計算）
                health_percent = enemy['health'] / (10 + self.stage * 2)
                gauge_width = int(enemy['width'] * health_percent)
                pyxel.rect(enemy['x'], enemy['y'] - 4, gauge_width, 2, 8)
                
                # ボスを目立たせるための輪郭
                pyxel.rectb(enemy['x'] - 1, enemy['y'] - 1, enemy['width'] + 2, enemy['height'] + 2, 8 + (pyxel.frame_count // 3) % 3)  # 点滅する輪郭
        
        # 弾の描画（数を制限）
        for shot in self.shots[:self.max_shots]:
            if shot['type'] == 'player':
                pyxel.rect(shot['x'], shot['y'], shot['width'], shot['height'], 11)
            else:
                pyxel.rect(shot['x'], shot['y'], shot['width'], shot['height'], 8)
        
        # パワーアップアイテムの描画
        for powerup in self.powerups:
            color = 11 if powerup['type'] == 'power' else 12
            pyxel.circ(powerup['x'], powerup['y'], 3, color)
        
        # プレイヤーの描画（無敵時はフラッシュさせる）
        if self.player['invincible'] == 0 or self.skip_frame % 4 < 2:
            # シールド有効時は輪郭を表示
            if self.player['shield'] > 0:
                pyxel.circb(self.player['x'] + 4, self.player['y'] + 4, 6, 12)
            
            pyxel.blt(self.player['x'], self.player['y'], 0, 0, 0, 8, 8, 0)
        
        # エフェクトの描画
        for exp in self.explosions:
            pyxel.circ(exp['x'], exp['y'], exp['radius'], exp['color'])
        
        # UI表示
        # スコア
        pyxel.text(4, 4, f"SCORE: {self.score}", 7)
        
        # 残機
        for i in range(self.player['lives']):
            pyxel.blt(4 + i * 10, 15, 0, 0, 0, 8, 8, 0)
        
        # パワーレベル
        pyxel.text(100, 4, f"POWER: {self.player['power_level']}", 11)
        
        # ステージ
        pyxel.text(100, 15, f"STAGE: {self.stage}", 12)
        
        # ボス出現ゲージの描画
        if not self.boss_appeared: # ボス出現前のみゲージ表示
            gauge_width = 50 # ゲージバーの幅
            gauge_height = 5  # ゲージバーの高さ
            gauge_x = 105     # ゲージバーのX座標
            gauge_y = 25      # ゲージバーのY座標
            
            # ゲージ背景
            pyxel.rectb(gauge_x, gauge_y, gauge_width, gauge_height, 1)
            # 現在のゲージ量
            current_gauge_width = int(gauge_width * (self.boss_gauge / self.boss_gauge_max))
            pyxel.rect(gauge_x, gauge_y, current_gauge_width, gauge_height, 8)
            # テキスト表示 (例: BOSS: 50%)
            pyxel.text(gauge_x - 20, gauge_y, f"BOSS:", 7)
            pyxel.text(gauge_x + gauge_width + 2, gauge_y, f"{int(self.boss_gauge / self.boss_gauge_max * 100)}%", 7)
    
    def draw_pause_screen(self):
        # 半透明の黒色オーバーレイ（交互の線で表現）
        for y in range(0, 140, 2):
            pyxel.line(0, y, 160, y, 0)
        
        # ポーズテキスト
        pyxel.text(65, 60, "PAUSED", 7)
        
        # 再開方法
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_START'):
            pyxel.text(45, 75, "PRESS START TO RESUME", 11)
        else:
            pyxel.text(45, 75, "PRESS ESC TO RESUME", 11)
    
    def draw_gameover(self):
        # ゲームオーバー画面の描画
        pyxel.text(60, 50, "GAME OVER", 8)
        pyxel.text(50, 70, f"FINAL SCORE: {self.score}", 7)
        pyxel.text(45, 90, "PRESS R TO RESTART", 11)
        
        # モバイル用テキスト
        if self.is_mobile:
            pyxel.text(55, 100, "OR TAP TO RESTART", 11)
        
        # ゲームパッド用のテキスト
        if hasattr(pyxel, 'GAMEPAD1_BUTTON_A'):
            pyxel.text(40, 110, "OR PRESS A TO RESTART", 11)
    
    def check_collision(self, obj1, obj2):
        # 単純な矩形衝突判定
        return not (
            obj1['x'] + obj1['width'] <= obj2['x'] or
            obj1['x'] >= obj2['x'] + obj2['width'] or
            obj1['y'] + obj1['height'] <= obj2['y'] or
            obj1['y'] >= obj2['y'] + obj2['height']
        )

# ゲーム開始
StarDefender()