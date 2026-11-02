"""A bounded, authored regional variant of Aquileia's JHZ partition.

Native reference: JER_proclaim_greater_aquileia. The common four-state border
is used by the regional settlements; the wider royal carveout is not imported.
No claimant globals, foreign subject land or JER post-victory focus tree.
"""
BORDER=(378,399,447,497)
POOL=(378,399,433,434,440,441,447,497,498,520,538,666,674,
      382,397,398,402,405,411,422,423,424,437,439,443,458,479,
      486,492,506,539,545,546,547,554,555,568,665)

def build_herzland(L,trig,effect,once,tt,focus,config,national,peaceful):
    trig('herzland_state','OR = { '+' '.join(f'state = {s}' for s in POOL)+' }')
    trig('border_state','OR = { '+' '.join(f'state = {s}' for s in BORDER)+' }')
    trig('can_partition','''HSM_AQR_national = yes has_war = no
GRI = { exists = no }
OR = {
 382 = { is_owned_and_controlled_by = PREV }
 AND = { JHZ = { is_subject_of = ROOT } 382 = { is_owned_and_controlled_by = JHZ } }
}
OR = { JHZ = { exists = no } JHZ = { is_subject_of = ROOT } }
NOT = { has_country_flag = HSM_AQR_partition_done }
''')
    trig('can_border','''HSM_AQR_national = yes has_war = no
has_country_flag = HSM_AQR_partition_done
JHZ = { exists = yes is_subject_of = ROOT }
any_owned_state = { HSM_AQR_border_state = yes is_fully_controlled_by = ROOT }
NOT = { has_country_flag = HSM_AQR_border_done }
''')
    # Every state is selected under the actual owner. No cores or controller shortcuts transfer land.
    effect('partition','''if = { limit = { HSM_AQR_can_partition = yes }
set_country_flag = HSM_AQR_partition_done
if = { limit = { JHZ = { exists = no } } set_country_flag = HSM_AQR_new_JHZ }
every_owned_state = {
 limit = { HSM_AQR_herzland_state = yes NOT = { HSM_AQR_border_state = yes } is_fully_controlled_by = PREV }
 remove_core_of = ROOT
 add_core_of = JHZ
 transfer_state_to = JHZ
}
puppet = JHZ
JHZ = { set_country_flag = JER_puppet set_country_flag = HSM_AQR_herzland_settlement }
if = { limit = { has_country_flag = HSM_AQR_new_JHZ }
 JHZ = {
  set_capital = { state = 382 remember_old_capital = no }
  inherit_technology = PREV
  load_focus_tree = { tree = generic_griffon_focus keep_completed = no }
 }
 clr_country_flag = HSM_AQR_new_JHZ
}
JHZ = {
  if = { limit = { ROOT = { OR = { has_country_flag = HSM_AQR_ratified_JEB_royal has_country_flag = HSM_AQR_ratified_JEB_constitutional has_country_flag = HSM_AQR_ratified_JRR_absolutist has_country_flag = HSM_AQR_ratified_JRR_coalition has_country_flag = HSM_AQR_ratified_JFT_dennis has_country_flag = HSM_AQR_ratified_VIN_gadiffer } } }
   set_cosmetic_tag = JER_PUPPET
   if = { limit = { ROOT = { has_government = democratic } } set_politics = { ruling_party = democratic elections_allowed = yes } }
   else = { set_politics = { ruling_party = neutrality elections_allowed = no } }
  }
  else_if = { limit = { ROOT = { has_government = fascism } }
   set_cosmetic_tag = JER_REPUBLIC_PUPPET set_politics = { ruling_party = fascism elections_allowed = no }
  }
  else_if = { limit = { ROOT = { has_government = communism } }
   set_cosmetic_tag = JER_REPUBLIC_PUPPET set_politics = { ruling_party = communism elections_allowed = no }
  }
  else_if = { limit = { ROOT = { has_government = neutrality } }
   set_cosmetic_tag = JER_REPUBLIC_PUPPET set_politics = { ruling_party = neutrality elections_allowed = no }
  }
  else = { set_cosmetic_tag = JER_REPUBLIC_PUPPET set_politics = { ruling_party = democratic elections_allowed = yes } }
}
}''')
    L('HSM_AQR_partition_tt','Transfer our fully controlled Herzland territories to the dependent government, retaining $STATE_378$, $STATE_399$, $STATE_447$ and $STATE_497$. Its government follows our constitutional settlement.','Передать зависимому правительству принадлежащие нам и полностью контролируемые земли Герцланда, сохранив $STATE_378$, $STATE_399$, $STATE_447$ и $STATE_497$. Его государственный строй будет соответствовать нашему устройству.')
    focus('partition',('A Government in Griffenheim','Правительство в Грифенхейме'),('The occupation offices cannot administer another country forever. Representatives from the Herzland towns will assemble in Griffenheim to form a dependent government, with its own officials and a written division of responsibilities. The border districts require a separate agreement.','Оккупационные канцелярии не могут вечно управлять чужой страной. Представители герцландских городов соберутся в Грифенхейме, чтобы учредить зависимое правительство со своими чиновниками и письменным разграничением полномочий. Для пограничных областей потребуется отдельное соглашение.'),27,13,('national_settlement',),tt('partition_req','Peace; independent Aquileia; the old Empire no longer exists; we or our Herzland subject own and fully control Griffenheim. Herzland is absent or already our subject.','Мир; независимая Аквелия; прежняя Империя больше не существует; мы или наш герцландский субъект владеем Грифенхеймом и полностью контролируем его. Герцланд отсутствует либо уже подчинён нам.','HSM_AQR_can_partition = yes'),'effect_tooltip = { puppet = JHZ } custom_effect_tooltip = HSM_AQR_partition_tt hidden_effect = { HSM_AQR_partition = yes }',cost=6)
    dispatch='\n'.join(f'if = {{ limit = {{ has_country_flag = HSM_AQR_ratified_{r[0]} }} country_event = {{ id = HSM_AQR.{300+i} days = 1 }} }}' for i,r in enumerate(config))
    effect('border','''if = { limit = { HSM_AQR_can_border = yes }
set_country_flag = HSM_AQR_border_done
every_owned_state = { limit = { HSM_AQR_border_state = yes is_fully_controlled_by = PREV } add_core_of = ROOT }
'''+dispatch+'\n}')
    L('HSM_AQR_border_tt','The border delegates will report on the new citizenship articles.','Пограничные делегаты представят отчёт о новых статьях гражданства.')
    border_preview = '\n'.join(f'{state} = {{ if = {{ limit = {{ is_owned_and_controlled_by = ROOT }} add_core_of = ROOT }} }}' for state in BORDER)
    focus('border',('The Border Articles','Пограничные статьи'),('Citizenship cannot be conveyed by moving a line on a staff map. Courts, schools and municipal councils need to know which law they will use tomorrow. Delegates from the border will sign the articles only after their place in the new settlement has been stated.','Гражданство нельзя передать, передвинув линию на штабной карте. Судам, школам и муниципальным советам необходимо знать, по какому закону они будут жить завтра. Пограничные делегаты подпишут статьи лишь после определения своего места в новом устройстве.'),27,14,('partition',),tt('border_req','Peace; the dependent Herzland government exists; own and fully control at least one of the four border districts.','Мир; зависимое герцландское правительство существует; хотя бы одна из четырёх пограничных областей принадлежит нам и полностью контролируется.','HSM_AQR_can_border = yes'),f'effect_tooltip = {{ {border_preview} }} custom_effect_tooltip = HSM_AQR_border_tt hidden_effect = {{ HSM_AQR_border = yes }}',cost=6)
    once('herzland_guarantees','HSM_AQR_national = yes JHZ = { exists = yes is_subject_of = ROOT }','JHZ = { add_stability = 0.10 add_political_power = 100 } add_political_power = 75')
    focus('herzland_guarantees',('A Treaty with a Signature','Договор с собственной подписью'),('The Herzland ministers will receive an office of their own at the treaty conference. The agreement must identify the obligations owed to Aquileia and those which Aquileia owes in return. Without that second column, a dependent government is only an occupation office with a different sign.','Герцландские министры получат собственное представительство на договорной конференции. Соглашение должно назвать обязательства перед Аквелией и встречные обязанности самой Аквелии. Без второй колонки зависимое правительство останется оккупационной канцелярией с другой вывеской.'),27,15,('partition',),national+peaceful+tt('subject_req','The Herzland government remains our subject.','Герцландское правительство остаётся нашим субъектом.','JHZ = { exists = yes is_subject_of = ROOT }'),'effect_tooltip = { JHZ = { add_stability = 0.10 add_political_power = 100 } add_political_power = 75 } hidden_effect = { HSM_AQR_herzland_guarantees = yes }',cost=5)


