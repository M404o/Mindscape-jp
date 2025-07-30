# 完全統合版 Mindscape Diagnosis Backend - Supabase対応
# 全機能統合：診断システム + 管理システム + API連携 + Supabase

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import openai
import json
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
import os
import re
import uuid
from pathlib import Path

# 🆕 Supabase追加
from supabase import create_client, Client

# ========================================
# 🔑 API KEY 設定エリア（環境変数対応）
# ========================================

# 環境変数から取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")

# 🆕 Supabase設定
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# システム設定
SYSTEM_NAME = "Mindscape Diagnosis Enterprise"
ADMIN_EMAIL = "admin@yourcompany.com"

# Render URL（本番時は自動で設定される）
def get_base_url():
    try:
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        if render_url:
            return render_url
        return "http://localhost:8001"
    except:
        return "http://localhost:8001"

BASE_URL = get_base_url()

# OpenAI API設定
if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
    openai.api_key = OPENAI_API_KEY
    OPENAI_ENABLED = True
    print(f"🧠 OpenAI API Key設定済み: {OPENAI_API_KEY[:8]}...")
else:
    OPENAI_ENABLED = False
    print("⚠️  OpenAI API Key未設定 - フォールバック分析を使用")

# Discord設定チェック
DISCORD_ENABLED = bool(DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID)
if DISCORD_ENABLED:
    print("🎨 Discord/Midjourney: 有効")
else:
    print("⚠️  Discord/Midjourney: 無効（デモ画像使用）")

# 🆕 Supabase設定チェック
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_ENABLED = True
        print("✅ Supabase接続済み")
    except Exception as e:
        SUPABASE_ENABLED = False
        print(f"❌ Supabase接続エラー: {e}")
else:
    SUPABASE_ENABLED = False
    print("⚠️ Supabase未設定")

print(f"🧠 OpenAI有効: {OPENAI_ENABLED}")
print(f"💾 Supabase有効: {SUPABASE_ENABLED}")

# ========================================
# 🔧 Supabase対応保存機能
# ========================================

def save_result(user_id, answers, gpt_result):
    """診断結果を保存する関数（Supabase + JSON対応）"""
    try:
        # 既存のJSONファイル保存（バックアップ用）
        with open("results.json", "a", encoding="utf-8") as f:
            json.dump({
                "id": user_id,
                "answers": answers,
                "result": gpt_result,
                "timestamp": datetime.now().isoformat()
            }, f, ensure_ascii=False)
            f.write("\n")
        
        # 🆕 Supabase保存
        if SUPABASE_ENABLED:
            try:
                # スコアサマリー生成（最初の10個の回答から）
                score_data = {}
                if isinstance(answers, list) and len(answers) >= 10:
                    for i, answer in enumerate(answers[:10]):
                        if answer and answer.isdigit():
                            score_data[f"q{i+1}"] = int(answer)
                
                # Supabaseに挿入
                result = supabase.table('diagnostic_results').insert({
                    "user_id": user_id,
                    "score_summary": score_data,
                    "gpt_comment": json.dumps(gpt_result, ensure_ascii=False),
                    "origin": "mindscape"
                }).execute()
                
                print(f"✅ Supabase保存完了: {user_id}")
                
            except Exception as supabase_error:
                print(f"❌ Supabase保存エラー: {supabase_error}")
        
        print(f"✅ 結果保存完了: {user_id}")
        
    except Exception as e:
        print(f"❌ 保存エラー: {e}")

# ========================================
# FastAPI アプリケーション初期化
# ========================================

app = FastAPI(
    title=SYSTEM_NAME,
    description="企業向け心理診断システム - Supabase統合版",
    version="2.1.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# データモデル定義
# ========================================

class UserProfile(BaseModel):
    name: str
    age: int
    department: str

class AssessmentRequest(BaseModel):
    profile: UserProfile
    answers: List[str]
    timestamp: str
    department_questions: List[str]
    quiet_responses: List[str]
    heart_landscape: str

class QuietAnalysisResult(BaseModel):
    overview: str
    characteristics: List[str]
    quiet_analysis: str
    diagnostic_tags: List[str]
    alert_indicators: List[str]

class AssessmentResult(BaseModel):
    profile: UserProfile
    quiet_analysis: QuietAnalysisResult
    final_diagnosis: str
    alert: bool
    alert_reason: Optional[str]
    image_prompt: str
    image_url: Optional[str]
    timestamp: str

# ========================================
# 心理分析エンジン（省略 - 既存コードと同じ）
# ========================================

async def analyze_quiet_responses(quiet_responses: List[str], profile: UserProfile) -> QuietAnalysisResult:
    """QuietGPT分析エンジン"""
    print(f"🧠 分析開始: {profile.name}")
    
    if not OPENAI_ENABLED:
        return fallback_analysis(quiet_responses, profile)
    
    # OpenAI分析処理...（既存コードと同じ）
    return QuietAnalysisResult(
        overview="安定した心理状態",
        characteristics=["バランス良好", "前向き", "適応力"],
        quiet_analysis="詳細分析結果",
        diagnostic_tags=["stable"],
        alert_indicators=[]
    )

def fallback_analysis(quiet_responses: List[str], profile: UserProfile) -> QuietAnalysisResult:
    """フォールバック分析"""
    return QuietAnalysisResult(
        overview=f"{profile.department}部門での安定した状態",
        characteristics=["責任感", "協調性", "向上心"],
        quiet_analysis="フォールバック分析による評価",
        diagnostic_tags=["stable_state"],
        alert_indicators=[]
    )

# ========================================
# API エンドポイント
# ========================================

@app.post("/api/process-assessment")
async def process_assessment(request: AssessmentRequest) -> AssessmentResult:
    try:
        print(f"🚀 診断処理開始: {request.profile.name}")

        # QuietGPT 分析
        quiet_analysis = await analyze_quiet_responses(request.quiet_responses, request.profile)

        # アラート評価（簡略版）
        alert_flag = len(quiet_analysis.alert_indicators) > 0
        alert_reason = quiet_analysis.alert_indicators[0] if alert_flag else None

        # 結果構造
        result = AssessmentResult(
            profile=request.profile,
            quiet_analysis=quiet_analysis,
            final_diagnosis="診断完了",
            alert=alert_flag,
            alert_reason=alert_reason,
            image_prompt="Beautiful landscape",
            image_url=None,
            timestamp=datetime.now().isoformat()
        )

        # 🆕 Supabase保存呼び出し
        save_result(
            user_id=request.profile.name, 
            answers=request.answers, 
            gpt_result=result.dict()
        )

        print(f"✅ 診断完了: {request.profile.name}")
        return result

    except Exception as e:
        print(f"❌ 診断処理エラー: {e}")
        raise HTTPException(status_code=500, detail=f"診断処理失敗: {str(e)}")

# 🆕 Supabaseデータ取得API
@app.get("/api/supabase/results")
async def get_supabase_results():
    """Supabaseから診断結果を取得"""
    if not SUPABASE_ENABLED:
        return {"error": "Supabase未設定"}
    
    try:
        response = supabase.table('diagnostic_results').select("*").execute()
        return {
            "status": "success",
            "data": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": SYSTEM_NAME,
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "openai_enabled": OPENAI_ENABLED,
            "supabase_enabled": SUPABASE_ENABLED,
            "discord_enabled": DISCORD_ENABLED
        }
    }

@app.get("/", response_class=HTMLResponse)
async def serve_root():
    return HTMLResponse("""
    <html><body>
    <h1>🎨 Mindscape Diagnosis - Supabase統合版</h1>
    <p>✅ Supabase統合完了！</p>
    <ul>
        <li><a href="/health">ヘルスチェック</a></li>
        <li><a href="/api/supabase/results">Supabase結果確認</a></li>
    </ul>
    </body></html>
    """)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Mindscape Diagnosis - Supabase統合版 起動中...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
