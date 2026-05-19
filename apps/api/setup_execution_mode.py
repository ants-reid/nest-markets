#!/usr/bin/env python
"""
Quick setup script to activate AUTO_PAPER execution mode.

Run: python setup_execution_mode.py [mode_name]
  mode_name: 'auto_paper' (default), 'paper', 'auto_live', or 'confirm_live'

This script:
1. Disables all currently active execution modes
2. Activates the selected mode
3. Configures approval/live trading flags per mode
"""

import sys
from sqlalchemy import create_engine, text
from app.config import settings
from app.db.models import ExecutionMode
from app.db.session import SessionLocal
from app.db.enums import ExecutionModeName

def setup_execution_mode(mode_name: str = "auto_paper"):
    """Activate the specified execution mode."""
    
    # Validate mode
    valid_modes = [m.value for m in ExecutionModeName]
    if mode_name not in valid_modes:
        print(f"❌ Invalid mode: {mode_name}")
        print(f"   Valid modes: {', '.join(valid_modes)}")
        sys.exit(1)
    
    session = SessionLocal()
    try:
        # Step 1: Disable all currently active modes
        active_modes = session.query(ExecutionMode).filter(
            ExecutionMode.is_active == True
        ).all()
        
        for mode in active_modes:
            mode.is_active = False
            print(f"  Disabled: {mode.name}")
        
        # Step 2: Get or create the target mode
        target_mode = session.query(ExecutionMode).filter(
            ExecutionMode.name == mode_name
        ).first()
        
        if not target_mode:
            # Create it
            target_mode = ExecutionMode(
                name=mode_name,
                is_active=True
            )
            session.add(target_mode)
            print(f"  Created new mode: {mode_name}")
        else:
            target_mode.is_active = True
            print(f"  Reactivated existing mode: {mode_name}")
        
        # Step 3: Configure mode-specific flags
        if mode_name == "auto_paper":
            target_mode.requires_approval = "inactive"  # No approval needed
            target_mode.allows_live_orders = "inactive"
            print(f"  ✅ AUTO_PAPER: Auto-submits paper trades (no approval)")
            
        elif mode_name == "paper":
            target_mode.requires_approval = "active"  # Manual approval required
            target_mode.allows_live_orders = "inactive"
            print(f"  ✅ PAPER: Manual approval required for each trade")
            
        elif mode_name == "confirm_live":
            target_mode.requires_approval = "active"
            target_mode.allows_live_orders = "inactive"  # Still disabled in MVP
            print(f"  ✅ CONFIRM_LIVE: User approval required before live execution")
            
        elif mode_name == "auto_live":
            target_mode.requires_approval = "inactive"
            target_mode.allows_live_orders = "inactive"  # Disabled in MVP
            print(f"  ✅ AUTO_LIVE: (Disabled in MVP, future: auto live execution)")
        
        session.commit()
        print(f"\n✨ Execution mode set to: {mode_name.upper()}\n")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto_paper"
    setup_execution_mode(mode)
