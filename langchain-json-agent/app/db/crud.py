from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Product
from typing import Optional, List


async def get_product_by_id(db: AsyncSession, product_id: str) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_products_by_category(db: AsyncSession, category: str) -> List[Product]:
    result = await db.execute(select(Product).where(Product.category == category))
    return result.scalars().all()


async def get_products_under_price(db: AsyncSession, price: float) -> List[Product]:
    result = await db.execute(select(Product).where(Product.price <= price))
    return result.scalars().all()
 
