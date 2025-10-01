"""
common/session_utils.py - Gemensamma session state utilities
===========================================================

Hanterar session state-läsning för både Streamlit och Dash.
Separerar UI-specifik session management från core-logik.

DESIGN:
- UI-filer använder dessa funktioner för att hämta org/user
- Core-funktioner tar org som parameter (testbart, UI-agnostiskt)
- Stödjer både Streamlit och Dash genom flexibel design
"""

import os
from typing import Optional, Any, Dict


# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def get_user_org(session_state: Optional[Dict[str, Any]] = None) -> str:
    """
    Hämtar organisations-ID från session state.
    
    Flexibel för både Streamlit och Dash:
    - Streamlit: Anropar utan argument, läser från st.session_state
    - Dash: Skicka in custom session dict
    
    Args:
        session_state: Session state dict (optional)
                      None = försök läsa från Streamlit
                      Dict = använd custom dict (för Dash)
        
    Returns:
        Organisations-ID (str), 'default' om inget hittas
        
    Examples:
        # Streamlit
        org = get_user_org()  # Läser från st.session_state
        
        # Dash  
        org = get_user_org(dash_session)  # Explicit dict
    """
    if session_state is None:
        # Försök läsa från Streamlit
        try:
            import streamlit as st
            return st.session_state.get('current_user', 'default')
        except ImportError:
            # Streamlit inte installerat
            return 'default'
        except Exception:
            # Annat fel (t.ex. körs utanför Streamlit-kontext)
            return 'default'
    
    # Använd skickad session state dict
    return session_state.get('current_user', 'default')


def get_user_dmu(session_state: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """
    Hämtar användarens DMU från session state (för företagsanvändare).
    
    Args:
        session_state: Session state dict (optional)
        
    Returns:
        DMU ID (int) eller None om ej företagsanvändare
    """
    if session_state is None:
        try:
            import streamlit as st
            return st.session_state.get('user_dmu', None)
        except:
            return None
    
    return session_state.get('user_dmu', None)


def get_user_role(session_state: Optional[Dict[str, Any]] = None) -> str:
    """
    Hämtar användarens roll från session state.
    
    Args:
        session_state: Session state dict (optional)
        
    Returns:
        User role: 'admin', 'company', 'viewer', 'default'
    """
    if session_state is None:
        try:
            import streamlit as st
            return st.session_state.get('user_role', 'default')
        except:
            return 'default'
    
    return session_state.get('user_role', 'default')


# ============================================================================
# KATALOGHANTERING MED SESSION STATE
# ============================================================================

def ensure_org_dir(base_path: str, session_state: Optional[Dict[str, Any]] = None) -> str:
    """
    Skapar organisationsspecifik katalog och returnerar sökvägen.
    
    Använder get_user_org() för att hämta org från session state,
    sedan skapar katalogstruktur: base_path/org/
    
    Args:
        base_path: Baskatalog (t.ex. "scenario/kapitalbas/exports_to_dea")
        session_state: Session state dict (optional)
        
    Returns:
        Fullständig sökväg till organisationsspecifik katalog
        
    Examples:
        # Streamlit
        export_dir = ensure_org_dir("scenario/kapitalbas/exports_to_dea")
        # Returnerar: "scenario/kapitalbas/exports_to_dea/organisation_x/"
        
        # Dash
        export_dir = ensure_org_dir("scenario/kapitalbas/exports_to_dea", dash_session)
    """
    org = get_user_org(session_state)
    org_path = os.path.join(base_path, org)
    os.makedirs(org_path, exist_ok=True)
    return org_path


def ensure_user_export_dir(
    export_type: str = "general",
    session_state: Optional[Dict[str, Any]] = None
) -> str:
    """
    Skapar användarspecifik exportkatalog baserat på export-typ.
    
    Convenience function som kombinerar org-läsning och katalog-skapande
    för vanliga export-scenarion.
    
    Args:
        export_type: Typ av export ('dea', 'ir', 'effektivitet', 'general')
        session_state: Session state dict (optional)
        
    Returns:
        Sökväg till organisationsspecifik exportkatalog
        
    Raises:
        ValueError: Om okänd export_type
    """
    base_paths = {
        'dea': 'scenario/kapitalbas/exports_to_dea',
        'ir': 'scenario/kapitalbas/exports_to_ir',
        'effektivitet': 'scenario/effektiviseringskrav/exports_to_ir',
        'general': 'scenario/exports'
    }
    
    if export_type not in base_paths:
        raise ValueError(
            f"Okänd export_type: {export_type}. "
            f"Giltiga: {list(base_paths.keys())}"
        )
    
    return ensure_org_dir(base_paths[export_type], session_state)


# ============================================================================
# HJÄLPFUNKTIONER FÖR FILHANTERING
# ============================================================================

def get_user_file_path(
    filename: str,
    subdir: str = "",
    session_state: Optional[Dict[str, Any]] = None
) -> str:
    """
    Skapar fullständig filsökväg i organisationsspecifik katalog.
    
    Args:
        filename: Filnamn (t.ex. "export.parquet")
        subdir: Underkatalog (t.ex. "scenario/exports")
        session_state: Session state dict (optional)
        
    Returns:
        Fullständig filsökväg: subdir/org/filename
    """
    org_dir = ensure_org_dir(subdir, session_state)
    return os.path.join(org_dir, filename)


# ============================================================================
# TESTER
# ============================================================================

if __name__ == "__main__":
    """
    Tester för session_utils.
    """
    print("Testing session_utils.py...")
    print("=" * 60)
    
    # Test 1: get_user_org utan Streamlit (fallback)
    print("\nTest 1: get_user_org() fallback")
    org = get_user_org()
    print(f"Org (no session): '{org}' (förväntat: 'default')")
    assert org == 'default', "Fallback misslyckades"
    
    # Test 2: get_user_org med custom dict
    print("\nTest 2: get_user_org() med custom dict")
    test_session = {'current_user': 'test_org_123'}
    org = get_user_org(test_session)
    print(f"Org (custom dict): '{org}' (förväntat: 'test_org_123')")
    assert org == 'test_org_123', "Custom dict misslyckades"
    
    # Test 3: ensure_org_dir skapar katalog
    print("\nTest 3: ensure_org_dir() skapar katalog")
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_base = os.path.join(tmpdir, "test_exports")
        org_dir = ensure_org_dir(test_base, test_session)
        
        expected = os.path.join(test_base, "test_org_123")
        print(f"Skapad katalog: {org_dir}")
        print(f"Förväntad: {expected}")
        
        assert org_dir == expected, "Katalog-path fel"
        assert os.path.exists(org_dir), "Katalog skapades inte"
    
    # Test 4: ensure_user_export_dir
    print("\nTest 4: ensure_user_export_dir()")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporärt ändra base path för test
        import sys
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            export_dir = ensure_user_export_dir('dea', test_session)
            expected_suffix = os.path.join('test_org_123')
            
            print(f"Export dir: {export_dir}")
            assert export_dir.endswith(expected_suffix), "Export dir fel suffix"
            assert os.path.exists(export_dir), "Export dir skapades inte"
        finally:
            os.chdir(original_cwd)
    
    # Test 5: get_user_file_path
    print("\nTest 5: get_user_file_path()")
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = get_user_file_path(
            "test.parquet",
            tmpdir,
            test_session
        )
        
        expected_filename = "test.parquet"
        expected_org = "test_org_123"
        
        print(f"Filsökväg: {filepath}")
        assert expected_filename in filepath, "Filename saknas"
        assert expected_org in filepath, "Org saknas"
    
    print("\n" + "=" * 60)
    print("Alla tester slutförda!")