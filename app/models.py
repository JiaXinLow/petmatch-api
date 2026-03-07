from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index

Base = declarative_base()

class Shelter(Base):
    __tablename__ = "shelters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(50), nullable=True, default="USA")

    pets = relationship("Pet", back_populates="shelter")

class Breed(Base):
    __tablename__ = "breeds"

    id = Column(Integer, primary_key=True, index=True)
    species = Column(String(20), nullable=False)   # Dog/Cat/Other
    name = Column(String(120), nullable=False)     # standardized name
    size = Column(String(20), nullable=True)
    group = Column(String(50), nullable=True)
    energy_level = Column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("species", "name", name="uq_breed_species_name"),
        Index("ix_breed_species_name", "species", "name"),
    )

    pets = relationship("Pet", back_populates="breed")

class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(50), nullable=False, index=True, unique=True)

    species = Column(String(20), nullable=False, index=True)
    breed_name_raw = Column(String(200), nullable=True)
    breed_id = Column(Integer, ForeignKey("breeds.id"), nullable=True)

    sex_upon_outcome = Column(String(50), nullable=True)
    age_months = Column(Integer, nullable=True)
    color = Column(String(120), nullable=True)

    outcome_type = Column(String(50), nullable=True, index=True)
    outcome_datetime = Column(DateTime, nullable=True)

    shelter_id = Column(Integer, ForeignKey("shelters.id"), nullable=True)

    breed = relationship("Breed", back_populates="pets")
    shelter = relationship("Shelter", back_populates="pets")