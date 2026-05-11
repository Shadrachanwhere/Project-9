from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
import csv

# Create SQLite database engine
engine = create_engine('sqlite:///inventory.db')

# Create base class for models
Base = declarative_base()


# Define Brand model
class Brand(Base):
    __tablename__ = 'brands'
    brand_id = Column(Integer, primary_key=True)
    brand_name = Column(String, nullable=False)


# Define Product model
class Product(Base):
    __tablename__ = 'products'
    
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    product_quantity = Column(Integer, nullable=False)
    product_price = Column(Float, nullable=False)
    date_updated = Column(DateTime, nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.brand_id'), nullable=False)


# Create session factory
Session = sessionmaker(bind=engine)        


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Database initialized: inventory.db")
    
    # Import brands from CSV
    session = Session()
    with open('brands.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            brand = Brand(brand_name=row['brand_name'])
            session.add(brand)
    session.commit()
    print("Brands imported from brands.csv")


