import discord
from discord.ui import View, Select

class RoleSelector(View):
    def __init__(self, bot, roles):
        super().__init__(timeout=None)
        self.bot = bot
        self.roles = roles
        self.add_item(RoleDropdown(roles))

class RoleDropdown(Select):
    def __init__(self, roles):
        options = [
            discord.SelectOption(label=role, description=f"Escolha o cargo {role}")
            for role in roles
        ]
        super().__init__(
            placeholder="Selecione até 3 cargos...",
            min_values=1,
            max_values=3,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        # Adicionar os cargos selecionados
        added_roles = []
        for role_name in self.values:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await member.add_roles(role)
                added_roles.append(role_name)

        await interaction.response.send_message(
            f"Cargos atribuídos: {', '.join(added_roles)}", ephemeral=True
        )

async def handle_role_selection(ctx, bot, roles):
    """Exibe o menu de seleção de cargos."""
    view = RoleSelector(bot, roles)
    await ctx.send("Selecione seus cargos no menu abaixo:", view=view)
