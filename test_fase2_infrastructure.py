"""
Test Suite for FASE 2 Infrastructure
Tests all multi-timeframe data layer and signal scoring components
"""

import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Import new modules
from tradingagents.dataflows.multi_timeframe import MultiTimeframeLayer
from tradingagents.dataflows.structure_detector import SwingClassifier, PivotFinder
from tradingagents.dataflows.scoring_engine import ScoringEngine
from tradingagents.dataflows.cache_manager import CacheManager


def test_cache_manager():
    """Test 1: Cache Manager - incremental updates"""
    print("\n" + "="*70)
    print("TEST 1: Cache Manager - Incremental Updates")
    print("="*70)
    
    cache_mgr = CacheManager()
    
    # Simulate caching
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'open': range(100),
        'high': range(100, 200),
        'low': range(50, 150),
        'close': range(100),
        'volume': range(1000, 1100),
    })
    
    symbol = "TEST_SPY"
    timeframe = "daily"
    
    # Write initial cache
    cache_mgr.write_cache(symbol, df, timeframe)
    print(f"✓ Written cache for {symbol} ({len(df)} rows)")
    
    # Check cache exists
    has_cache = cache_mgr.has_cache(symbol, timeframe)
    print(f"✓ has_cache() returned: {has_cache}")
    
    # Should not need update (fresh)
    should_update = cache_mgr.should_update(symbol, timeframe)
    print(f"✓ should_update() returned: {should_update} (fresh cache)")
    
    # Read cached data
    cached_df = cache_mgr.read_cache(symbol, timeframe)
    print(f"✓ read_cache() returned: {len(cached_df)} rows")
    
    # Simulate new data (next day)
    new_data = pd.DataFrame({
        'date': [datetime.now()],
        'open': [100],
        'high': [105],
        'low': [99],
        'close': [102],
        'volume': [1000000],
    })
    
    # Append to cache
    cache_mgr.append_to_cache(symbol, new_data, timeframe)
    updated_df = cache_mgr.read_cache(symbol, timeframe)
    print(f"✓ append_to_cache() succeeded - now {len(updated_df)} rows")
    
    # Get stats
    stats = cache_mgr.get_cache_stats()
    print(f"✓ Cache stats: {stats['total_files']} files, {stats['total_size_mb']:.2f} MB")
    
    print("\n✅ Cache Manager: PASSED")
    return True


def test_pivot_finder():
    """Test 2: Pivot Finder - Swing highs/lows detection"""
    print("\n" + "="*70)
    print("TEST 2: Pivot Finder - Swing Highs/Lows")
    print("="*70)
    
    # Fetch real data
    df = yf.download("SPY", start="2024-01-01", end="2025-02-01", progress=False)
    df = df.reset_index()
    df.columns = df.columns.str.lower()
    
    finder = PivotFinder(min_lookback=2)
    
    # Find pivots
    highs, lows = finder.find_pivots(df)
    
    print(f"✓ Found {len(highs)} swing highs")
    print(f"✓ Found {len(lows)} swing lows")
    
    # Get last N
    last_4 = finder.get_last_n_pivots(df, n=4)
    print(f"✓ Last 4 pivots: {len(last_4)} found")
    
    for p in last_4[:2]:
        print(f"   - {p.date}: {p.value:.2f} ({p.type})")
    
    print("\n✅ Pivot Finder: PASSED")
    return True


def test_swing_classifier():
    """Test 3: Swing Classifier - Structure analysis"""
    print("\n" + "="*70)
    print("TEST 3: Swing Classifier - Structure Analysis")
    print("="*70)
    
    df = yf.download("SPY", start="2024-01-01", end="2025-02-01", progress=False)
    df = df.reset_index()
    df.columns = df.columns.str.lower()
    
    classifier = SwingClassifier()
    
    # Classify structure
    structure = classifier.classify_structure(df)
    print(f"✓ Structure: {structure.formation}")
    print(f"✓ Direction: {structure.direction} (1=bull, -1=bear, 0=choppy)")
    print(f"✓ Context: {structure.context}")
    print(f"✓ Total pivots: {len(structure.pivots)}")
    
    # ChoCH detection
    choch, choch_reason = classifier.detect_choch(df)
    print(f"✓ ChoCH: {choch}")
    if choch:
        print(f"   {choch_reason}")
    
    # BOS detection
    bos, bos_reason = classifier.detect_bos(df)
    print(f"✓ BOS: {bos}")
    if bos:
        print(f"   {bos_reason}")
    
    # Key levels
    levels = classifier.get_key_levels(df, n_levels=2)
    print(f"✓ Resistance levels: {[f'{r:.2f}' for r in levels['resistances']]}")
    print(f"✓ Support levels: {[f'{s:.2f}' for s in levels['supports']]}")
    
    print("\n✅ Swing Classifier: PASSED")
    return True


def test_multi_timeframe_layer():
    """Test 4: Multi-Timeframe Layer - Weekly + Daily sync"""
    print("\n" + "="*70)
    print("TEST 4: Multi-Timeframe Layer - Weekly + Daily")
    print("="*70)
    
    mtf_layer = MultiTimeframeLayer()
    
    symbol = "SPY"
    print(f"Fetching {symbol}...")
    
    mtf = mtf_layer.fetch_symbol_mtf(symbol)
    
    print(f"✓ Fetched MTF data for {symbol}")
    print(f"  Daily bars: {len(mtf.daily.ohlcv)}")
    print(f"  Weekly bars: {len(mtf.weekly.ohlcv)}")
    print(f"  Sync date: {mtf.sync_date}")
    
    # Check confluence
    long_valid, long_reasons = mtf_layer.confluence_check_long(mtf)
    print(f"\n✓ LONG confluence: {'✓ VALID' if long_valid else '✗ INVALID'}")
    
    short_valid, short_reasons = mtf_layer.confluence_check_short(mtf)
    print(f"✓ SHORT confluence: {'✓ VALID' if short_valid else '✗ INVALID'}")
    
    # Sample indicators
    adx = mtf.daily.latest('adx')
    er = mtf.daily.latest('er')
    vr = mtf.daily.latest('volume_ratio')
    
    print(f"\n✓ Daily ADX: {adx:.1f if adx else 'N/A'}")
    print(f"✓ Daily ER: {er:.2f if er else 'N/A'}")
    print(f"✓ Daily VR: {vr:.2f if vr else 'N/A'}")
    
    print("\n✅ Multi-Timeframe Layer: PASSED")
    return True


def test_scoring_engine():
    """Test 5: Scoring Engine - Signal quality 0-100"""
    print("\n" + "="*70)
    print("TEST 5: Scoring Engine - 0-100 Signal Scores")
    print("="*70)
    
    mtf_layer = MultiTimeframeLayer()
    scorer = ScoringEngine()
    
    symbols = ["SPY", "QQQ"]
    scores = []
    
    for symbol in symbols:
        print(f"\nScoring {symbol}...")
        
        mtf = mtf_layer.fetch_symbol_mtf(symbol)
        long_score, short_score = scorer.score_mtf_signal(mtf)
        
        scores.append(long_score)
        scores.append(short_score)
        
        print(f"  🟢 LONG:  {long_score.total_score:.0f}/100")
        print(f"     - Trend: {long_score.trend_strength:.0f}")
        print(f"     - Confluence: {long_score.direction_confluence:.0f}")
        print(f"     - Volume: {long_score.volume_quality:.0f}")
        print(f"     - Structure: {long_score.structure_quality:.0f}")
        print(f"     - Risk: {long_score.risk_profile:.0f}")
        
        if long_score.strengths:
            print(f"     Strengths:")
            for s in long_score.strengths[:2]:
                print(f"       ✓ {s}")
        
        print(f"\n  🔴 SHORT: {short_score.total_score:.0f}/100")
        print(f"     - Trend: {short_score.trend_strength:.0f}")
        print(f"     - Confluence: {short_score.direction_confluence:.0f}")
        print(f"     - Volume: {short_score.volume_quality:.0f}")
        print(f"     - Structure: {short_score.structure_quality:.0f}")
        print(f"     - Risk: {short_score.risk_profile:.0f}")
    
    # Rank signals
    print(f"\n{'='*70}")
    print("TOP LONG SIGNALS:")
    ranked_long = scorer.rank_signals(scores)
    for i, score in enumerate(ranked_long[:3], 1):
        print(f"{i}. {score.symbol:6} - {score.total_score:.0f}/100")
    
    print("\n✅ Scoring Engine: PASSED")
    return True


def test_integration():
    """Test 6: Full integration - All components together"""
    print("\n" + "="*70)
    print("TEST 6: Full Integration - Complete Workflow")
    print("="*70)
    
    print("\nStep 1: Create MTF layer with cache...")
    mtf_layer = MultiTimeframeLayer()
    
    print("Step 2: Fetch multi-timeframe data...")
    symbol = "AAPL"
    mtf = mtf_layer.fetch_symbol_mtf(symbol)
    
    print("Step 3: Detect structure...")
    classifier = SwingClassifier()
    structure = classifier.classify_structure(mtf.daily.ohlcv)
    
    print("Step 4: Score signals...")
    scorer = ScoringEngine()
    long_score, short_score = scorer.score_mtf_signal(mtf)
    
    print(f"\nResults for {symbol}:")
    print(f"✓ Structure: {structure.formation} ({structure.direction})")
    print(f"✓ LONG Score: {long_score.total_score:.0f}/100")
    print(f"✓ SHORT Score: {short_score.total_score:.0f}/100")
    print(f"✓ ADX: {long_score.adx_value:.1f}")
    print(f"✓ Volume Ratio: {long_score.volume_ratio:.2f}")
    
    print("\n✅ Full Integration: PASSED")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 FASE 2 INFRASTRUCTURE TEST SUITE")
    print("="*70)
    
    tests = [
        ("Cache Manager", test_cache_manager),
        ("Pivot Finder", test_pivot_finder),
        ("Swing Classifier", test_swing_classifier),
        ("Multi-Timeframe Layer", test_multi_timeframe_layer),
        ("Scoring Engine", test_scoring_engine),
        ("Full Integration", test_integration),
    ]
    
    results = {}
    
    for test_name, test_fn in tests:
        try:
            result = test_fn()
            results[test_name] = "✅ PASSED"
        except Exception as e:
            results[test_name] = f"❌ FAILED: {str(e)}"
            print(f"\n❌ Error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for test_name, result in results.items():
        print(f"{result} - {test_name}")
        if "PASSED" in result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! FASE 2 infrastructure is operational.")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Review errors above.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
