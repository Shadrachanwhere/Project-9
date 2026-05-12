from datetime import datetime
from pathlib import Path
import csv
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker

# Constants
DATA_DIR = Path('.')
DATABASE_FILE = DATA_DIR / 'inventory.db'
BRANDS_CSV = DATA_DIR / 'brands.csv'
INVENTORY_CSV = DATA_DIR / 'inventory.csv'
BRANDS_BACKUP_CSV = DATA_DIR / 'brands_backup.csv'
INVENTORY_BACKUP_CSV = DATA_DIR / 'inventory_backup.csv'
LOW_STOCK_THRESHOLD = 10

# Database setup
engine = create_engine(f'sqlite:///{DATABASE_FILE}')
Base = declarative_base()
Session = sessionmaker(bind=engine)


class Brand(Base):
    __tablename__ = 'brands'
    brand_id = Column(Integer, primary_key=True)
    brand_name = Column(String, nullable=False, unique=True)

    def __repr__(self) -> str:
        return f'<Brand id={self.brand_id} name={self.brand_name!r}>'


class Product(Base):
    __tablename__ = 'products'
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String, nullable=False)
    product_quantity = Column(Integer, nullable=False)
    product_price = Column(Float, nullable=False)
    date_updated = Column(DateTime, nullable=False)
    brand_id = Column(Integer, ForeignKey('brands.brand_id'), nullable=False)

    def __repr__(self) -> str:
        return (
            f'<Product id={self.product_id} name={self.product_name!r} '
            f'qty={self.product_quantity} price={self.product_price} date={self.date_updated} '
            f'brand_id={self.brand_id}>'
        )


# Utility helpers

def normalize_text(value: str) -> str:
    return value.strip()


def format_price(value: float) -> str:
    return f'${value:.2f}'


def format_date(value: datetime) -> str:
    return value.strftime('%m/%d/%Y')


def parse_int(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None


def parse_float(value: str) -> Optional[float]:
    try:
        return float(value.replace('$', '').strip())
    except ValueError:
        return None


def prompt_text(prompt: str, allow_empty: bool = False) -> str:
    while True:
        answer = input(prompt).strip()
        if answer or allow_empty:
            return answer
        print('Entry cannot be empty.')


def prompt_integer(prompt: str, allow_empty: bool = False) -> Optional[int]:
    while True:
        answer = input(prompt).strip()
        if not answer and allow_empty:
            return None
        value = parse_int(answer)
        if value is not None:
            return value
        print('Please enter a valid integer.')


def prompt_choice(prompt: str, valid_choices: set[str]) -> str:
    while True:
        answer = input(prompt).strip().upper()
        if answer in valid_choices:
            return answer
        print(f'Invalid option. Enter one of: {", ".join(sorted(valid_choices))}.')


def get_brand_name(session, brand_id: int) -> str:
    brand = session.query(Brand).filter_by(brand_id=brand_id).first()
    return brand.brand_name if brand else 'Unknown'


def get_brand_by_name(session, brand_name: str) -> Optional[Brand]:
    normalized = normalize_text(brand_name)
    return (
        session.query(Brand)
        .filter(func.lower(Brand.brand_name) == normalized.lower())
        .first()
    )


def get_brand_by_id(session, brand_id: int) -> Optional[Brand]:
    return session.query(Brand).filter_by(brand_id=brand_id).first()


# Database import and initialization

def create_tables() -> None:
    Base.metadata.create_all(engine)


def load_brands(session) -> None:
    session.query(Brand).delete()
    with BRANDS_CSV.open('r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            brand_name = normalize_text(row.get('brand_name', ''))
            if not brand_name:
                continue
            if get_brand_by_name(session, brand_name) is None:
                session.add(Brand(brand_name=brand_name))
    session.commit()


def load_products(session) -> None:
    with INVENTORY_CSV.open('r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            brand_name = normalize_text(row.get('brand_name', ''))
            product_name = normalize_text(row.get('product_name', ''))
            product_price = parse_float(row.get('product_price', '0'))
            product_quantity = parse_int(row.get('product_quantity', '0'))
            date_text = normalize_text(row.get('date_updated', ''))

            if not brand_name or not product_name or product_price is None or product_quantity is None or not date_text:
                continue

            brand = get_brand_by_name(session, brand_name)
            if brand is None:
                print(f"Warning: Brand '{brand_name}' not found, skipping product '{product_name}'.")
                continue

            try:
                date_updated = datetime.strptime(date_text, '%m/%d/%Y')
            except ValueError:
                print(f"Warning: Invalid date '{date_text}' for product '{product_name}'.")
                continue

            existing_product = session.query(Product).filter_by(product_name=product_name).first()
            if existing_product:
                if date_updated > existing_product.date_updated:
                    existing_product.product_quantity = product_quantity
                    existing_product.product_price = product_price
                    existing_product.date_updated = date_updated
                    existing_product.brand_id = brand.brand_id
                    print(f'Updated existing product: {product_name}')
            else:
                session.add(
                    Product(
                        product_name=product_name,
                        product_quantity=product_quantity,
                        product_price=product_price,
                        date_updated=date_updated,
                        brand_id=brand.brand_id,
                    )
                )
    session.commit()


def initialize_database() -> None:
    create_tables()
    with Session() as session:
        load_brands(session)
        load_products(session)


# Product operations

def display_product(product: Product, brand_name: str) -> None:
    print('\nProduct details:')
    print('Product ID:', product.product_id)
    print('Name:', product.product_name)
    print('Quantity:', product.product_quantity)
    print('Price:', format_price(product.product_price))
    print('Last updated:', format_date(product.date_updated))
    print('Brand:', brand_name)


def view_product_details() -> None:
    with Session() as session:
        products = session.query(Product).order_by(Product.product_id).all()
        if not products:
            print('No products available.')
            return

        print('\nAvailable products:')
        for product in products:
            print(f'{product.product_id}: {product.product_name}')

        while True:
            user_input = prompt_text('\nEnter product ID to view, or type Q to return: ')
            if user_input.upper() == 'Q':
                print('Returning to the main menu.')
                return

            product_id = parse_int(user_input)
            if product_id is None:
                print('Invalid entry. Please enter a numeric product ID or Q to quit.')
                continue

            product = session.query(Product).filter_by(product_id=product_id).first()
            if product is None:
                print(f'No product with ID {product_id} found. Please try again.')
                continue

            brand_name = get_brand_name(session, product.brand_id)
            display_product(product, brand_name)

            while True:
                action = prompt_choice('Choose an option: (E)dit, (D)elete, (R)eturn: ', {'E', 'D', 'R'})
                if action == 'E':
                    edit_product(session, product)
                    return
                if action == 'D':
                    delete_product(session, product)
                    return
                print('Returning to the main menu.')
                return


# Edit / delete

def edit_product(session, product: Product) -> None:
    print('\nLeave a field blank to keep the current value.')
    new_name = prompt_text(f'Product name [{product.product_name}]: ', allow_empty=True)
    new_price = prompt_text(f'Product price [{format_price(product.product_price)}]: ', allow_empty=True)
    new_quantity = prompt_text(f'Product quantity [{product.product_quantity}]: ', allow_empty=True)

    if new_name:
        product.product_name = new_name

    if new_price:
        parsed_price = parse_float(new_price)
        if parsed_price is not None:
            product.product_price = parsed_price
        else:
            print('Price not updated: invalid value.')

    if new_quantity:
        parsed_quantity = parse_int(new_quantity)
        if parsed_quantity is not None:
            product.product_quantity = parsed_quantity
        else:
            print('Quantity not updated: invalid value.')

    brands = session.query(Brand).order_by(Brand.brand_id).all()
    if brands:
        print('\nAvailable brands:')
        for brand in brands:
            print(f'{brand.brand_id}: {brand.brand_name}')
        print(f'Current brand ID: {product.brand_id}')
        while True:
            new_brand_id = prompt_text('Enter brand ID to assign, or leave blank to keep current: ', allow_empty=True)
            if not new_brand_id:
                break
            parsed_brand_id = parse_int(new_brand_id)
            if parsed_brand_id is None:
                print('Please enter a valid numeric brand ID or leave blank.')
                continue
            brand = get_brand_by_id(session, parsed_brand_id)
            if brand is None:
                print(f'Brand ID {parsed_brand_id} not found.')
                continue
            product.brand_id = brand.brand_id
            break
    else:
        print('No brands are available to choose from.')

    product.date_updated = datetime.now()
    session.commit()
    print('Product updated successfully.')


def delete_product(session, product: Product) -> None:
    confirm = prompt_choice(f'Are you sure you want to delete "{product.product_name}"? (Y/N): ', {'Y', 'N'})
    if confirm == 'Y':
        session.delete(product)
        session.commit()
        print('Product deleted successfully.')
    else:
        print('Delete cancelled.')


# Add operations

def add_new_brand() -> None:
    with Session() as session:
        while True:
            brand_name = prompt_text('Brand name: ')
            if get_brand_by_name(session, brand_name) is None:
                session.add(Brand(brand_name=brand_name))
                session.commit()
                print(f'Added new brand: {brand_name}')
                return
            print(f'Brand "{brand_name}" already exists. Please try again.')


def add_new_product() -> None:
    with Session() as session:
        product_name = prompt_text('Product name: ')
        existing_product = session.query(Product).filter_by(product_name=product_name).first()
        if existing_product:
            choice = prompt_choice(
                f'Product "{product_name}" already exists. Edit existing product? (Y/N): ',
                {'Y', 'N'},
            )
            if choice == 'Y':
                edit_product(session, existing_product)
                return
            return

        product_price = None
        while product_price is None:
            product_price = parse_float(prompt_text('Product price: '))
            if product_price is None:
                print('Please enter a valid price.')

        product_quantity = prompt_integer('Product quantity: ')
        brands = session.query(Brand).order_by(Brand.brand_id).all()
        if not brands:
            print('No brands are available. Please add brands first.')
            return

        print('\nAvailable brands:')
        for brand in brands:
            print(f'{brand.brand_id}: {brand.brand_name}')

        brand_id = None
        while brand_id is None:
            brand_id = prompt_integer('Enter brand ID: ')
            if get_brand_by_id(session, brand_id) is None:
                print(f'Brand ID {brand_id} does not exist.')
                brand_id = None

        session.add(
            Product(
                product_name=product_name,
                product_price=product_price,
                product_quantity=product_quantity,
                date_updated=datetime.now(),
                brand_id=brand_id,
            )
        )
        session.commit()
        print(f'Added new product: {product_name}')


def add_menu() -> None:
    while True:
        print('\nAdd menu:')
        print('1 - Add a new product')
        print('2 - Add a new brand')
        print('Q - Return to the main menu')

        choice = prompt_choice('Enter your choice: ', {'1', '2', 'Q'})
        if choice == '1':
            add_new_product()
            return
        if choice == '2':
            add_new_brand()
            return
        print('Returning to the main menu.')
        return


# Analysis and backup

def view_analysis() -> None:
    with Session() as session:
        total_products = session.query(Product).count()
        total_brands = session.query(Brand).count()

        most_expensive = session.query(Product).order_by(Product.product_price.desc()).first()
        least_expensive = session.query(Product).order_by(Product.product_price).first()

        top_brand = (
            session.query(Brand.brand_name, func.count(Product.product_id).label('product_count'))
            .join(Product, Product.brand_id == Brand.brand_id)
            .group_by(Brand.brand_id)
            .order_by(func.count(Product.product_id).desc())
            .first()
        )

        total_value = session.query(func.sum(Product.product_price * Product.product_quantity)).scalar() or 0
        low_stock = session.query(Product).filter(Product.product_quantity < LOW_STOCK_THRESHOLD).all()

        print('Total brands:', total_brands)
        print('Total products:', total_products)
        print(f'Total inventory value: {format_price(total_value)}')

        if most_expensive:
            print('\nMost expensive item:')
            print('  Name:', most_expensive.product_name)
            print('  Price:', format_price(most_expensive.product_price))
            print('  Brand:', get_brand_name(session, most_expensive.brand_id))
        else:
            print('\nMost expensive item: none')

        if least_expensive:
            print('\nLeast expensive item:')
            print('  Name:', least_expensive.product_name)
            print('  Price:', format_price(least_expensive.product_price))
            print('  Brand:', get_brand_name(session, least_expensive.brand_id))
        else:
            print('\nLeast expensive item: none')

        if top_brand:
            print('\nBrand with the most products:')
            print('  Brand:', top_brand.brand_name)
            print('  Product count:', top_brand.product_count)
        else:
            print('\nBrand with the most products: none')

        if low_stock:
            print('\nProducts with low stock (< 10 units):')
            for product in low_stock:
                print(f'  {product.product_name}: {product.product_quantity} units')
        else:
            print('\nNo products with low stock.')

        input('\nPress Enter to return to the main menu.')


def backup_database() -> None:
    with Session() as session:
        with BRANDS_BACKUP_CSV.open('w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['brand_name'])
            for brand in session.query(Brand).order_by(Brand.brand_id).all():
                writer.writerow([brand.brand_name])

        with INVENTORY_BACKUP_CSV.open('w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['brand_name', 'product_name', 'product_price', 'product_quantity', 'date_updated'])
            products = (
                session.query(Product, Brand.brand_name)
                .join(Brand, Product.brand_id == Brand.brand_id)
                .order_by(Product.product_id)
                .all()
            )
            for product, brand_name in products:
                writer.writerow([
                    brand_name,
                    product.product_name,
                    format_price(product.product_price),
                    product.product_quantity,
                    format_date(product.date_updated),
                ])

    print(f'CSV backup created: {BRANDS_BACKUP_CSV.name} and {INVENTORY_BACKUP_CSV.name}')


# Main interaction

def run_interaction() -> None:
    while True:
        print('\nChoose an option:')
        print('V - View single product details')
        print('N - Add a new brand or product')
        print('A - View an analysis')
        print('B - Backup the database')
        print('Q - Quit')

        choice = prompt_choice('Enter your choice: ', {'V', 'N', 'A', 'B', 'Q'})
        if choice == 'V':
            view_product_details()
        elif choice == 'N':
            add_menu()
        elif choice == 'A':
            view_analysis()
        elif choice == 'B':
            backup_database()
        else:
            print('Quitting.')
            break


def main() -> None:
    create_tables()
    print(f'Database initialized: {DATABASE_FILE.name}')
    initialize_database()
    run_interaction()


if __name__ == '__main__':
    main()
