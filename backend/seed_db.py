"""
seed_db.py

One-time script to populate the PostgreSQL database with the existing
mock data from the frontend TypeScript files.

Run once after creating the DB tables:
  python seed_db.py

Prerequisites:
  - Tables already created (run `python create_tables.py` first)
  - DATABASE_URL set in .env
"""

import asyncio
from dotenv import load_dotenv
load_dotenv()

from database import AsyncSessionLocal
from models import Supplier, BiodiversitySupplier, ThreatenedSpecies


# ── Epic 1 seed data (from mock-suppliers.ts) ─────────────────────────────────

SUPPLIERS = [
    dict(id="SUP-001", name="GreenLeaf Timber Co", abn="53004085616",
         address="14 Mill Road, Daintree QLD 4873", commodity="Timber",
         region="Far North Queensland", confidence_score=94, status="pending",
         is_validated=False, file_name="greenleaf_invoice.pdf", file_type="pdf"),
    dict(id="SUP-002", name="Oceanic Fisheries", abn="12345678901",
         address="", commodity="Seafood", region="Western Australia",
         confidence_score=41, status="pending", is_validated=False,
         warnings='["Missing address"]', file_name="oceanic_cert.png", file_type="image"),
    dict(id="SUP-003", name="Murray Basin Grains", abn="98765432100",
         address="Lot 5, Hay NSW 2711", commodity="Grain", region="Riverina",
         confidence_score=88, status="pending", is_validated=False,
         file_name="murray_basin.pdf", file_type="pdf"),
    dict(id="SUP-004", name="TasPure Salmon", abn="",
         address="Macquarie Harbour, Strahan TAS", commodity="",
         region="Tasmania", confidence_score=55, status="pending",
         is_validated=False, warnings='["ABN not found","Commodity unclear"]',
         file_name="taspure_doc.pdf", file_type="pdf"),
    dict(id="SUP-005", name="Pilbara Mining Svcs", abn="11223344556",
         address="Newman WA", commodity="Iron Ore", region="Pilbara",
         confidence_score=32, status="pending", is_validated=False,
         file_name="pilbara_mining.png", file_type="image"),
    dict(id="SUP-006", name="Kakadu Wild Foods", abn="66778899001",
         address="Jabiru NT 0886", commodity="Bush Foods", region="Top End",
         confidence_score=78, status="pending", is_validated=False,
         file_name="kakadu_wild.pdf", file_type="pdf"),
    dict(id="SUP-007", name="Barossa Valley Wines", abn="44556677889",
         address="23 Vine Lane, Tanunda SA 5352", commodity="Wine Grapes",
         region="Barossa Valley", confidence_score=96, status="pending",
         is_validated=False, file_name="barossa_wines.csv", file_type="csv"),
]


# ── Epic 2 seed data (from epic2-data.ts) ─────────────────────────────────────

BIO_SUPPLIERS = [
    dict(
        id="SUP-001", name="Daintree Timber Co.", region="Far North Queensland",
        lat=-16.25, lng=145.42, risk_score=87, risk_level="critical",
        protected_area_overlap=42, threatened_species_count=34,
        vegetation_condition=28, deforestation_rate=2.4, water_stress_index=31,
        carbon_stock=285, last_assessment="2026-03-12", industry="Forestry & Logging",
        notes="Adjacent to Daintree National Park. High overlap with World Heritage Area.",
        species=[
            dict(name="Southern Cassowary",            species_type="bird",   status="endangered"),
            dict(name="Bennett's Tree-kangaroo",        species_type="mammal", status="endangered"),
            dict(name="Spotted-tailed Quoll",           species_type="mammal", status="vulnerable"),
            dict(name="Daintree River Ringtail Possum", species_type="mammal", status="critically_endangered"),
        ],
    ),
    dict(
        id="SUP-002", name="Kimberley Pastoral Ltd.", region="Kimberley, WA",
        lat=-15.77, lng=128.74, risk_score=72, risk_level="high",
        protected_area_overlap=28, threatened_species_count=19,
        vegetation_condition=45, deforestation_rate=1.8, water_stress_index=68,
        carbon_stock=142, last_assessment="2026-02-28", industry="Pastoral & Grazing",
        notes="Operations near Mitchell River National Park. Seasonal flooding impacts.",
        species=[
            dict(name="Northern Quoll",    species_type="mammal",  status="endangered"),
            dict(name="Gouldian Finch",    species_type="bird",    status="endangered"),
            dict(name="Freshwater Sawfish", species_type="reptile", status="vulnerable"),
        ],
    ),
    dict(
        id="SUP-003", name="Tarkine Minerals Pty.", region="North-West Tasmania",
        lat=-41.75, lng=145.25, risk_score=64, risk_level="high",
        protected_area_overlap=35, threatened_species_count=22,
        vegetation_condition=52, deforestation_rate=0.9, water_stress_index=18,
        carbon_stock=320, last_assessment="2026-03-05", industry="Mining & Extraction",
        notes="Tarkine rainforest — one of the largest temperate rainforests globally.",
        species=[
            dict(name="Tasmanian Devil",         species_type="mammal", status="endangered"),
            dict(name="Giant Freshwater Crayfish", species_type="insect", status="vulnerable"),
            dict(name="Wedge-tailed Eagle (Tas.)", species_type="bird",   status="endangered"),
        ],
    ),
    dict(
        id="SUP-004", name="Murray Basin Agri.", region="Murray-Darling Basin, NSW",
        lat=-34.75, lng=143.92, risk_score=51, risk_level="medium",
        protected_area_overlap=12, threatened_species_count=11,
        vegetation_condition=61, deforestation_rate=0.5, water_stress_index=82,
        carbon_stock=45, last_assessment="2026-01-18", industry="Agriculture",
        notes="Extreme water stress. Irrigation dependent operations.",
        species=[
            dict(name="Plains-wanderer", species_type="bird",    status="critically_endangered"),
            dict(name="Murray Cod",      species_type="reptile", status="vulnerable"),
        ],
    ),
    dict(
        id="SUP-005", name="Great Southern Plantation", region="Gippsland, VIC",
        lat=-37.82, lng=147.61, risk_score=38, risk_level="medium",
        protected_area_overlap=8, threatened_species_count=9,
        vegetation_condition=72, deforestation_rate=0.3, water_stress_index=35,
        carbon_stock=198, last_assessment="2026-02-10", industry="Plantation Forestry",
        notes="Buffer zones maintained. Active rehabilitation programs.",
        species=[
            dict(name="Leadbeater's Possum", species_type="mammal", status="critically_endangered"),
            dict(name="Long-footed Potoroo", species_type="mammal", status="endangered"),
        ],
    ),
    dict(
        id="SUP-006", name="Cape York Resources", region="Cape York, QLD",
        lat=-14.45, lng=143.85, risk_score=79, risk_level="high",
        protected_area_overlap=38, threatened_species_count=27,
        vegetation_condition=39, deforestation_rate=2.1, water_stress_index=25,
        carbon_stock=210, last_assessment="2026-03-01", industry="Mining & Extraction",
        notes="Overlaps with Indigenous Protected Areas. Wet season access limitations.",
        species=[
            dict(name="Palm Cockatoo",           species_type="bird",   status="vulnerable"),
            dict(name="Golden-shouldered Parrot", species_type="bird",   status="endangered"),
            dict(name="Northern Bettong",         species_type="mammal", status="endangered"),
        ],
    ),
    dict(
        id="SUP-007", name="Adelaide Hills Organics", region="Adelaide Hills, SA",
        lat=-35.02, lng=138.72, risk_score=22, risk_level="low",
        protected_area_overlap=3, threatened_species_count=5,
        vegetation_condition=85, deforestation_rate=0.1, water_stress_index=45,
        carbon_stock=95, last_assessment="2026-03-10", industry="Agriculture",
        notes="Certified organic. Strong biodiversity management plan.",
        species=[
            dict(name="Yellow-footed Rock-wallaby", species_type="mammal", status="vulnerable"),
        ],
    ),
    dict(
        id="SUP-008", name="Pilbara Iron Works", region="Pilbara, WA",
        lat=-22.31, lng=118.35, risk_score=58, risk_level="medium",
        protected_area_overlap=15, threatened_species_count=13,
        vegetation_condition=55, deforestation_rate=0.7, water_stress_index=91,
        carbon_stock=32, last_assessment="2026-02-22", industry="Mining & Extraction",
        notes="Extreme water stress region. Mine site rehabilitation in progress.",
        species=[
            dict(name="Pilbara Olive Python", species_type="reptile", status="vulnerable"),
            dict(name="Ghost Bat",            species_type="mammal",  status="vulnerable"),
            dict(name="Northern Quoll",       species_type="mammal",  status="endangered"),
        ],
    ),
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Epic 1 suppliers
        for data in SUPPLIERS:
            existing = await db.get(Supplier, data["id"])
            if not existing:
                db.add(Supplier(**data))
                print(f"  + Supplier {data['id']} — {data['name']}")
            else:
                print(f"  ~ Supplier {data['id']} already exists, skipping.")

        # Epic 2 biodiversity suppliers
        for data in BIO_SUPPLIERS:
            species_list = data.pop("species", [])
            existing = await db.get(BiodiversitySupplier, data["id"])
            if not existing:
                supplier = BiodiversitySupplier(**data)
                db.add(supplier)
                await db.flush()
                for sp in species_list:
                    db.add(ThreatenedSpecies(supplier_id=supplier.id, **sp))
                print(f"  + BiodiversitySupplier {data['id']} — {data['name']} ({len(species_list)} species)")
            else:
                print(f"  ~ BiodiversitySupplier {data['id']} already exists, skipping.")

        await db.commit()
        print("\n✅ Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
