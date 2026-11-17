"""
Telegram bot: approximate nutrition calculator for foods and recipes.
It provides informational estimates per food/recipe portion only.
It does not set daily calorie targets or give weight-loss advice.
"""

import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Values are approximate per 100 g. Replace/add foods using reliable package labels.
FOODS = {
    "курица": {"kcal": 165, "p": 31.0, "f": 3.6, "c": 0.0},
    "рис варёный": {"kcal": 130, "p": 2.7, "f": 0.3, "c": 28.0},
    "гречка варёная": {"kcal": 110, "p": 3.6, "f": 1.1, "c": 20.0},
    "яйцо": {"kcal": 155, "p": 13.0, "f": 11.0, "c": 1.1},
    "банан": {"kcal": 89, "p": 1.1, "f": 0.3, "c": 22.8},
    "яблоко": {"kcal": 52, "p": 0.3, "f": 0.2, "c": 13.8},
    "овсянка варёная": {"kcal": 71, "p": 2.5, "f": 1.5, "c": 12.0},
    "творог 5%": {"kcal": 121, "p": 17.0, "f": 5.0, "c": 1.8},
    "молоко": {"kcal": 60, "p": 3.2, "f": 3.3, "c": 4.8},
    "картофель варёный": {"kcal": 87, "p": 1.9, "f": 0.1, "c": 20.1},
    "лосось": {"kcal": 208, "p": 20.0, "f": 13.0, "c": 0.0},
    "помидор": {"kcal": 18, "p": 0.9, "f": 0.2, "c": 3.9},
    "огурец": {"kcal": 15, "p": 0.7, "f": 0.1, "c": 3.6},
}

def nutrition_for(food_name: str, grams: float):
    item = FOODS[food_name]
    factor = grams / 100
    return {key: value * factor for key, value in item.items()}

def format_result(name: str, grams: float, values: dict) -> str:
    return (
        f"<b>{name.capitalize()} — {grams:g} г</b>\n"
        f"Энергетическая ценность: <b>{values['kcal']:.0f} ккал</b>\n"
        f"Белки: {values['p']:.1f} г\n"
        f"Жиры: {values['f']:.1f} г\n"
        f"Углеводы: {values['c']:.1f} г\n\n"
        "<i>Это приблизительная справочная оценка. Точные значения смотрите на упаковке.</i>"
    )

HELP = (
    "Я показываю примерное КБЖУ продуктов и простых рецептов.\n\n"
    "<b>Команды:</b>\n"
    "/foods — список продуктов\n"
    "/calc продукт; граммы — расчёт продукта\n"
    "/recipe — как посчитать рецепт\n\n"
    "<b>Пример:</b>\n"
    "<code>/calc банан; 120</code>\n\n"
    "Можно также отправить несколько строк в формате:\n"
    "<code>курица; 150\nрис варёный; 180</code>\n\n"
    "Бот не рассчитывает нормы питания, ограничения или цели по весу."
)

async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN. Создайте токен у BotFather и задайте переменную окружения.")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def start(message: Message):
        await message.answer("Привет! Я калькулятор примерного КБЖУ продуктов.\n\n" + HELP)

    @dp.message(Command("help"))
    async def help_command(message: Message):
        await message.answer(HELP)

    @dp.message(Command("foods"))
    async def foods(message: Message):
        names = "\n".join(f"• {name}" for name in sorted(FOODS))
        await message.answer("<b>Продукты в базе:</b>\n" + names)

    @dp.message(Command("recipe"))
    async def recipe(message: Message):
        await message.answer(
            "Чтобы посчитать рецепт, отправь продукты построчно:\n"
            "<code>курица; 150\nрис варёный; 180\nпомидор; 80</code>\n\n"
            "Я сложу значения всех ингредиентов. Для результата на 1 порцию "
            "раздели общий вес/значения на число порций самостоятельно."
        )

    @dp.message(Command("calc"))
    async def calc(message: Message):
        raw = (message.text or "").replace("/calc", "", 1).strip()
        await calculate_text(message, raw)

    async def calculate_text(message: Message, raw: str):
        if not raw:
            await message.answer("Укажи продукт и массу, например: <code>банан; 120</code>")
            return

        totals = {"kcal": 0.0, "p": 0.0, "f": 0.0, "c": 0.0}
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        parsed = []

        for line in lines:
            parts = [part.strip().lower() for part in line.split(";")]
            if len(parts) != 2:
                await message.answer(f"Не понял строку: <code>{line}</code>\nФормат: продукт; граммы")
                return
            name, grams_text = parts
            if name not in FOODS:
                await message.answer(
                    f"Продукта «{name}» нет в базе. Посмотри список: /foods"
                )
                return
            try:
                grams = float(grams_text.replace(",", "."))
                if grams <= 0 or grams > 10000:
                    raise ValueError
            except ValueError:
                await message.answer("Масса должна быть числом больше 0 (в граммах).")
                return
            values = nutrition_for(name, grams)
            parsed.append((name, grams, values))
            for key in totals:
                totals[key] += values[key]

        if len(parsed) == 1:
            name, grams, values = parsed[0]
            await message.answer(format_result(name, grams, values))
            return

        details = "\n".join(
            f"• {name}: {grams:g} г" for name, grams, _ in parsed
        )
        await message.answer(
            "<b>Ингредиенты:</b>\n" + details +
            "\n\n<b>Итого для всего рецепта:</b>\n"
            f"Энергетическая ценность: <b>{totals['kcal']:.0f} ккал</b>\n"
            f"Белки: {totals['p']:.1f} г\n"
            f"Жиры: {totals['f']:.1f} г\n"
            f"Углеводы: {totals['c']:.1f} г\n\n"
            "<i>Оценка приблизительная и относится ко всему рецепту, а не к дневной норме.</i>"
        )

    @dp.message(F.text)
    async def plain_text(message: Message):
        await calculate_text(message, message.text or "")

    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
