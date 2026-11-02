"""Compact native-label previews for variable-backed national spirit changes."""
MODIFIERS = {
    'army_org_factor':'MODIFIER_ARMY_ORG_FACTOR',
    'army_defence_factor':'MODIFIERS_ARMY_DEFENCE_FACTOR',
    'stability_factor':'MODIFIER_STABILITY_FACTOR',
    'political_power_factor':'MODIFIER_POLITICAL_POWER_FACTOR',
    'consumer_goods_factor':'MODIFIER_CONSUMER_GOODS_FACTOR',
    'production_speed_buildings_factor':'MODIFIER_PRODUCTION_SPEED_BUILDINGS_FACTOR',
    'mobilization_speed':'MODIFIER_MOBILIZATION_SPEED',
    'industrial_capacity_factory':'MODIFIER_INDUSTRIAL_CAPACITY_FACTOR',
    'supply_consumption_factor':'MODIFIER_SUPPLY_CONSUMPTION_FACTOR',
    'max_planning_factor':'MODIFIER_MAX_PLANNING_FACTOR',
    'industrial_capacity_dockyard':'MODIFIER_INDUSTRIAL_CAPACITY_DOCKYARD_FACTOR',
    'production_factory_max_efficiency_factor':'MODIFIER_PRODUCTION_FACTORY_MAX_EFFICIENCY_FACTOR',
    'research_speed_factor':'MODIFIER_RESEARCH_SPEED_FACTOR',
    'local_resources_factor':'MODIFIER_LOCAL_RESOURCES_FACTOR',
}


def spirit_changes(values):
    lines=[]
    for key,value in values.items():
        beneficial = value < 0 if key in ('consumer_goods_factor','supply_consumption_factor') else value > 0
        colour='G' if beneficial else 'R'
        lines.append(f'${MODIFIERS[key]}$: §{colour}{value:+.1%}§!')
    body='\n'.join(lines)
    return ('Modify §Y$HSM_AQR_compact$§! by:\n'+body,
            'Изменение национального духа «§Y$HSM_AQR_compact$§!»:\n'+body)
