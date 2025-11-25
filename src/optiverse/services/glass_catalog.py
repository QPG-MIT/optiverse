"""
Glass catalog and refractive index database for optical materials.

Provides refractive index calculations using Sellmeier equation
for common optical glasses (Schott, Ohara, etc.).
"""

import logging
import math
from typing import Dict, Optional

_logger = logging.getLogger(__name__)


class GlassCatalog:
    """
    Refractive index database for optical materials.

    Supports common glasses with Sellmeier dispersion formula:
        n² - 1 = B₁λ²/(λ² - C₁) + B₂λ²/(λ² - C₂) + B₃λ²/(λ² - C₃)

    Where λ is wavelength in micrometers.

    Example usage:
        catalog = GlassCatalog()
        n = catalog.get_refractive_index("N-BK7", 0.5876)  # Helium d-line
        print(f"BK7 @ 587.6nm: n = {n:.4f}")
    """

    def __init__(self):
        self._catalog: Dict[str, Dict] = {}
        self._load_builtin_catalog()

    def get_refractive_index(
        self,
        glass_name: str,
        wavelength_um: float = 0.5876
    ) -> Optional[float]:
        """
        Get refractive index for glass at specified wavelength.

        Args:
            glass_name: Material name (e.g., "N-BK7", "N-LAK22")
            wavelength_um: Wavelength in micrometers (default: 587.6nm, He d-line)

        Returns:
            Refractive index, or None if glass not found
        """
        # Normalize glass name
        glass_name = glass_name.upper().strip()

        # Special cases
        if glass_name in ["", "AIR", "VACUUM"]:
            return 1.0

        if glass_name not in self._catalog:
            return None

        glass_data = self._catalog[glass_name]

        # Calculate using appropriate formula
        formula_type = glass_data.get("formula", "Sellmeier")

        if formula_type == "Sellmeier":
            return self._calculate_sellmeier(glass_data["coefficients"], wavelength_um)
        elif formula_type == "Constant":
            return glass_data["index"]
        else:
            return None

    def _calculate_sellmeier(self, coefficients: list, wavelength_um: float) -> float:
        """
        Calculate refractive index using Sellmeier equation.

        Args:
            coefficients: [B1, B2, B3, C1, C2, C3]
            wavelength_um: Wavelength in micrometers

        Returns:
            Refractive index
        """
        B1, B2, B3, C1, C2, C3 = coefficients
        lam_sq = wavelength_um ** 2

        n_squared = 1.0 + (
            B1 * lam_sq / (lam_sq - C1) +
            B2 * lam_sq / (lam_sq - C2) +
            B3 * lam_sq / (lam_sq - C3)
        )

        return math.sqrt(n_squared)

    def _load_builtin_catalog(self):
        """Load built-in glass catalog with Sellmeier coefficients."""
        # Sellmeier coefficients from Schott and other manufacturers
        # Format: {name: {formula: "Sellmeier", coefficients: [B1, B2, B3, C1, C2, C3]}}

        self._catalog = {
            # Schott glasses
            "N-BK7": {
                "formula": "Sellmeier",
                "manufacturer": "Schott",
                "coefficients": [
                    1.03961212,     # B1
                    0.231792344,    # B2
                    1.01046945,     # B3
                    0.00600069867,  # C1
                    0.0200179144,   # C2
                    103.560653      # C3
                ],
            },
            "N-LAK22": {
                "formula": "Sellmeier",
                "manufacturer": "Schott",
                "coefficients": [
                    1.14229781,
                    0.535138441,
                    1.04088385,
                    0.00585778594,
                    0.0198546147,
                    100.834017
                ],
            },
            "N-SF6HT": {
                "formula": "Sellmeier",
                "manufacturer": "Schott",
                "coefficients": [
                    1.77931763,
                    0.338149866,
                    2.08734474,
                    0.0133714182,
                    0.0617533621,
                    174.01759
                ],
            },
            "N-SF11": {
                "formula": "Sellmeier",
                "manufacturer": "Schott",
                "coefficients": [
                    1.73759695,
                    0.313747346,
                    1.89878101,
                    0.013188707,
                    0.0623068142,
                    155.23629
                ],
            },
            "N-F2": {
                "formula": "Sellmeier",
                "manufacturer": "Schott",
                "coefficients": [
                    1.39757037,
                    0.159201403,
                    1.2686543,
                    0.00995906143,
                    0.0546931752,
                    119.248346
                ],
            },
            "SF11": {
                "formula": "Sellmeier",
                "manufacturer": "Schott",
                "coefficients": [
                    1.73759695,
                    0.313747346,
                    1.89878101,
                    0.013188707,
                    0.0623068142,
                    155.23629
                ],
            },
            # Fused Silica
            "FUSED_SILICA": {
                "formula": "Sellmeier",
                "manufacturer": "Various",
                "coefficients": [
                    0.6961663,
                    0.4079426,
                    0.8974794,
                    0.00467914826,
                    0.0135120631,
                    97.9340025
                ],
            },
            "SILICA": {
                "formula": "Sellmeier",
                "manufacturer": "Various",
                "coefficients": [
                    0.6961663,
                    0.4079426,
                    0.8974794,
                    0.00467914826,
                    0.0135120631,
                    97.9340025
                ],
            },
            # Common constants (for quick lookup)
            "WATER": {
                "formula": "Constant",
                "index": 1.333
            },
            "SAPPHIRE": {
                "formula": "Constant",
                "index": 1.77
            },
        }

    def list_glasses(self) -> list:
        """Return list of available glass names."""
        return sorted(self._catalog.keys())

    def get_glass_info(self, glass_name: str) -> Optional[Dict]:
        """Get full information about a glass."""
        glass_name = glass_name.upper().strip()
        return self._catalog.get(glass_name)


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    catalog = GlassCatalog()

    # Test at common wavelengths
    wavelengths = [
        (0.486, "F (blue)"),
        (0.5876, "d (yellow)"),
        (0.656, "C (red)"),
        (0.7065, "706.5nm (NIR)"),
    ]

    for glass in ["N-BK7", "N-LAK22", "N-SF6HT"]:
        _logger.info(f"\n{glass}:")
        for wl, desc in wavelengths:
            n = catalog.get_refractive_index(glass, wl)
            if n:
                _logger.info(f"  {desc:15s} {wl:.4f}µm: n = {n:.5f}")



