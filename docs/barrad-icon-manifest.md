# Barrad Icon Manifest

Current coverage, 2026-10-08: **135/135 focuses, 32/32 ideas and 6/6 dynamic modifiers** use custom artwork. This includes intentional thematic reuse, not one unique illustration per definition. The library contains **83 source motifs**: the unchanged historical 45 below and 38 newly reviewed motifs.

Reviewed on 2026-10-01: **45/45 assets**, covering all **34 Service focuses** with unique internal icons and **11 shared civilian cover motifs**. Each has a transparent source PNG, a 99x86 RGBA TGA and matching standard/shine sprites.

This is a dedicated Barrad snapshot, not a Cyanolisia approval migration. "Reviewed" records source/native-size visual inspection and technical validation; in-game rendering remains unverified. Hashes identify these reviewed revisions, not image-format validity.

## Files and Review

- Source: `art/source/<ID>.png`; export: `mod/HoISubmod/gfx/interface/goals/<ID>.tga`.
- Sprites: `GFX_<ID>` and `GFX_<ID>_shine` in `interface/HSM_BAR_service_icons.gfx` and `interface/HSM_BAR_service_icons_shine.gfx`.
- [Subject/prompt inventory](../art/barrad-service-art-brief.md).
- [Batch A review](barrad-art-batch-a.md) and [native-size preview](../art/previews/HSM_BAR_batch_a_99x86.png).
- [Batch B review](barrad-art-batch-b.md) and [native-size dark/light preview](barrad-art-batch-b-review.png).
- Historical notes retain the repairs to empty drawer/doorplate details, Earth-like globe markings, background haze and an invented date/name. No outstanding artistic defect identified in the final sheets.
- Dual focus names/descriptions and the **SP-only icon masking limitation** are documented in [implementation notes](barrad-implementation.md#archive-and-presentation).

Run on Windows with PowerShell 7.2+:

```powershell
pwsh -NoProfile -File tools/Test-BarradArt.ps1
```

Result: **45 asset scenarios passed; 0 failed**. Decoded PNG transparency/dimensions, TGA payload/alpha and standard/shine references checked. This test does not enforce the historical hashes below.

## Reviewed Revisions

All rows: **REVIEWED**, no active next action. Compare both hashes before treating later edited files as the same reviewed revision.

| ID | Source PNG SHA-256 | Export TGA SHA-256 |
| --- | --- | --- |
| `HSM_BAR_cover_accounts` | `9da525ce06c89c8b0b8c27788a7dc5e9141c6af4eb26bde23d72cbc2b87203d2` | `9b4e9f7f58f7f7273eba088df6e04d1b37aa4c707b94ad6f40f693c0c939dc08` |
| `HSM_BAR_cover_archives` | `e6894633cb6dfa17bf83f062379665685dd7d9838ab3f99617f2d430695075d2` | `b0c6c3dd15a07ce4355287e491b88193f016ae95892724823c6d9ae730d5da2b` |
| `HSM_BAR_cover_charter` | `2182156107a5f3c869949f1eceac4d2a053461f9a130ad93ec9ee51d7f41ed86` | `4babd0a3ad6f784092b03ffabd23bfd13cdb980dc51e6adecf59817d0b9e6a72` |
| `HSM_BAR_cover_clinic` | `8b1a0dabec303bfc58334f24a9e4efcd1dabcd47ae43eb61e7870e193236e736` | `a649cfdccdff15076a6994c28d0a01ea4db2dc035016c9133a2367766cf7686f` |
| `HSM_BAR_cover_laboratory` | `d3193eebef0153d1552c1eb53c52f6778a2edae6bcf1b7f1d1b4b7df5a5426bb` | `d44e988ba904583d1799b62b41ed8fa123e2079f5f384e3dc445bfe469ca0e26` |
| `HSM_BAR_cover_office` | `5770a7cbc25722b9b22b5c4d6feb84d3f73058ecb12a2fb23276c3fd2f6453f9` | `4cad27124260668fc797d917209e19a605bb88236fa5306ea781faab077493d4` |
| `HSM_BAR_cover_post` | `d5c42a2e361dd8dd3f7cb206a9905a4f70ceac4cf3b6efb610c7cdff84a75fc7` | `eca57aab1137bdeb73c381d41272114179cb0fce04d975e5a937f4c2ad2cf688` |
| `HSM_BAR_cover_shipping` | `3aacb3fa82c4e21bde6773a419a9791a00a0b4ed76b39633a25ce2db1d419687` | `fd9520ec1ed80ef47d2ded5decaf6f993e622f423526bdf33ca7103f1cb19e73` |
| `HSM_BAR_cover_survey` | `1deb6fa67fd74d3b61da89b3c192934a1053eedf2f8a5b3888411f541e052fcf` | `0611adfbf0c0d45c38c559bfb7d9a3546f91f46c6d8aa57e0d49eaad2b6c9b7f` |
| `HSM_BAR_cover_warehouse` | `db810c073830f4d69acbb026c95fd3954eb93570dd2c5b0c3ecd361d425c3447` | `8e0139b7543b02ada2ca4acf2c3acb9bb0f0025881bf62859469129f18da159b` |
| `HSM_BAR_cover_workshop` | `a036d0f2a36097d02ea482198e330ae11f16470e4d9593270b0c1fc5cc7b8f76` | `446b9a05dce26994a5770a09e635aecf94a75c80d97b64d03d7ead7b48d0d659` |
| `HSM_BAR_dir_activation` | `50f4a721229ac630f859a98d202ec1477e41f1ebe9506b32fa669d45f08d3d47` | `6407fc566d5be2afa35ba68d873e990afb929bad2a7feda4359ad66426016c2a` |
| `HSM_BAR_dir_aftermath` | `cd681ea742192d76999c9a951ee5092ced0c5e3d214571d1cac30919d37f00a1` | `ab35b51a3eeef23915ebc30c2363430f0cb79a8288df7c30132791bf76836e35` |
| `HSM_BAR_dir_agency` | `0718e658b329536017a24a998bd4496dde0f9476421a61bf43e628a2f3f4c463` | `afdce7968558024d16bd14d115e1a14e89a522e57caf52cea335d917183dea9c` |
| `HSM_BAR_dir_archives` | `6259ba9b4648a3c52045cb8af90a2d8211bbfc5caae99c79572f370c3866635e` | `095a4c015bae5cee26c2a9e23e29067160e4424f42079c1346c5acf22be97033` |
| `HSM_BAR_dir_charter` | `316aa1bd5475d283af3dbf5641a9445c7613c252bd24f8808ceea243472dc351` | `add9df7c5255c186d6fcc21cd947d58591510cd64a1f7dc8f6b9558f7fd074ab` |
| `HSM_BAR_dir_coexistence` | `f9578b841b29c61e4d1b1322b56adb7641876634576aed06078ca50502baa98d` | `7b85bbb0c997bc31a42e40fd1407512df5c139199d6dc12d9beab6ed64d326d5` |
| `HSM_BAR_dir_commission` | `ccea7de9e887e53d63bfa10b5c2b5cbcdd2df5151624922a8862acc0b026ad36` | `4a26db67a5b8db9f7ff25353a6e363dbf342b29e73cf5c01983b9326d243cbbd` |
| `HSM_BAR_dir_countercult` | `6922b617190088ebc5d21e7b728229154342361c6c8c4475f0e8748577a158c0` | `d5faf4f9930bd56e4e14c7d396ab3d2534cc42c62ff6766a40c7d01af97c11c1` |
| `HSM_BAR_dir_custody_law` | `e2dab5fd8a8124d4bfde032ddf4004fceeea03e77c48b286abfd14d3908a5161` | `dff8c3fe3dc086033676bb569a52733d3fbafa9e1bff9ed733286b94c92a0433` |
| `HSM_BAR_dir_equus` | `62749b8cb5f8401c659fd3f24e2b70f902a0fb7f5cf5066baaafb5b719f75c8f` | `c576e621de8dc8f5da04494394137f4db6611d97db3c479d94a3b567079fe69c` |
| `HSM_BAR_dir_evidence` | `3cf7077750abaa827d81b9fc9c1462b08f6e6881806637571510a7e8af3c89ef` | `ebfaf59a947a78f839619a6128ed122fb9c84aac8e7441f1325deb8a1b5241e8` |
| `HSM_BAR_dir_foreign_mandate` | `37c545d3d301bbce6b1f15ff1775aa8eab3140ff8a3625b7b39c3464013eea55` | `53fb429993031236368e4fcb12d9396a85ad0ef80224efe4a7fc40ec9b1afa10` |
| `HSM_BAR_dir_foreign_protocol` | `bbf46b72c0eaf7564e2c919824b45c853dea7557c191831a8fd4ea5894e88678` | `8a711f313b2532591cb08019d628dc911a3198f2dc402e36b68a8c93384187c9` |
| `HSM_BAR_dir_griffonia` | `2ec259bc9562e50308039cc96615d90dddefab5d50ac9f18b02b2d2315a9177e` | `4d55d9479da892d0f76213371a56abca3b7421f955de6e2f05154027c8492c28` |
| `HSM_BAR_dir_liaison` | `8d43ec993a0f21d8061c4da341c853660393ac64c3987cf1fcfb676943f5bce6` | `23df7aebd77ea86805b8fab7fea13b772c186565058a5989bc0e7b6107752b09` |
| `HSM_BAR_dir_names` | `94f3c604a63f34c019cf34115c4bcdfa729cf0a36d62cf305265ccaa20250fb0` | `cf854cd987b681245c8acd9a1b4724ab88d89782f32b94674f154d3594d6c71a` |
| `HSM_BAR_dir_normalization` | `bed12cf847630ac4a9830e6b8b497e96913c349e4681edce102af2f79ababde8` | `62b854da8f543a65e4d8e2a1eb1985cd44b8a967335e5528014d984edfdaf853` |
| `HSM_BAR_dir_north` | `daca6b83d24aa1caf821271d50bd3a06116c770b59a1376af4b21a4455f6a93a` | `6bd0ca27fbb307b30dbaaf7a4bc19619c6b98de1507c0e43d12b9903e73deb9a` |
| `HSM_BAR_dir_open_report` | `1547535549eb06bbceb28a9b5a07749ccc97b3349831640b14bc9937af88c50b` | `105278ed557d927bcbe3ed02e0cb929bbcc7db72e3fbd6ede955181ee56d024b` |
| `HSM_BAR_dir_quiet_watch` | `43d0d07993256bf94ef919cbfbe43e7ce6a6124b5323ccc66adbd76d2a7dab6f` | `c3338a038c6930663ae32209bd3f80130ef089c75632254ac31306efc894bf10` |
| `HSM_BAR_dir_radio` | `fb96c1a3d945f142a83f4ff9874c508c02f3ddd5686d567e70662a3cbfbc3f3c` | `a6ad366e97abfc02e5dbbf3ff9e90fb8f225c65146756cc2ac87ccc456094183` |
| `HSM_BAR_dir_register` | `8113dcb8981da0e552c2143c8ec05bb293f48f3446cebed305ec72585ac2080b` | `8496a8041779f32738c2f364b9333beb8373d496054ce37128e285ae7dbdbb1d` |
| `HSM_BAR_dir_remains` | `43e54e58a903ca2896700fd87fbe17346f249bb2e1b47bd7a0898ae009a517c9` | `9105e47a06eb3e24076ab8eb733de7744f68534fecb80768e832d9300a9960db` |
| `HSM_BAR_dir_riverlands` | `f85e2700963cdafcc4045efc9b420698af79f1a1563989da64b20c195ed921f4` | `de184d26c6a8b5e4060502483b48bef63c771a5e43a981e1c651d6d315bf674c` |
| `HSM_BAR_dir_rulers` | `fcd86166d0088bf07ee43dc10e7067060c59d1fdd69db4438a5b03350e05fe36` | `3c17e3f23ea88610f0c954780846ea18d7224a9407a16e0f15a97bf3662ef932` |
| `HSM_BAR_dir_seal_labs` | `2ac1069adaf7db3b78792554b1c1fed1d14d9cd5f844535e5cf64c7b35f0fdb0` | `760105492aeb5f4212b9feffc4b3967a41652c6882e304ada4d8f50aceef5a31` |
| `HSM_BAR_dir_sealed_orders` | `205c53ee0c6f565a2f5702490a98ab5442198e8bed0773c1b6ffeefdf0acf9fc` | `f20e96f49d20ada681302ae803f5f6314c87b821733d116cf873ab89443274f7` |
| `HSM_BAR_dir_storage` | `004bcca137c32e0be629a1e11f7c087f35ea612a8b759776cc1333676446c354` | `4c93a9754cccc367a6a7378740470e65f1faedb8e6734f99afcf6bde042b468f` |
| `HSM_BAR_dir_suppression_lab` | `d9bbbe6c16093df16e6c3f36935c601dee3833cf4182f5ca6d5387aa85a20ee1` | `0be64656e877dc08048b5111f9c19fe949a42eb1b41485fd43e3ab9063fad57c` |
| `HSM_BAR_dir_trafficking` | `032516082cd85f9d7194cd7a9bf0ef47264ea6b8830b86f90eeea65a405ce323` | `14ab3d4113d383c70eacbb3ae328484d7d29ba3a2b95699a45987bd845dd7d02` |
| `HSM_BAR_dir_training` | `75a5fab33a48b21c93a01b8f2555523fb213db3c158ae6df0203ea8f61a0f45f` | `1fb134baab3999db59d5851a91cc128f2ef41e1bcc7833c1b0d1e0a03b54f76f` |
| `HSM_BAR_dir_watchmen` | `0913235d6b8c94befe472adde4c954dd280c689a0249210c4d02582e856940f9` | `23ea48f0be067b797a747e5ff9278e24d23a42f2b0d5cfe48a02f32638c65356` |
| `HSM_BAR_dir_world` | `e76ad47d202adcadb6f860e56eacc373bd9ea31a7b5f3cf5db85ee872f641401` | `90230c4fb4c2845a080b476d8c30af250637a77d3f05dd686e51a13c486aee30` |
| `HSM_BAR_dir_zebrica` | `15e79823c9b9a8daf68e8affc0e5ef1d1241bbc49192dff3ada953ea6e30860e` | `8f3a3f2c26ebec6481870a453e4e7bab408725313eff90aac042a56e30fb7027` |

## Content Batch, 2026-10-08

**38/38 new source/goal pairs and 29/29 idea exports reviewed**, with no active artistic correction identified. All sources were inspected individually; the actual 99x86 and 64x64 TGA exports were inspected on dark and light backgrounds. This is not in-game approval.

- [Subjects, prompts, references and repairs](../art/barrad-content-icons.md).
- [Goal contact sheet](../art/previews/HSM_BAR_content_goals_native.png), [idea contact sheet](../art/previews/HSM_BAR_content_ideas_native.png).
- [Mappings and conversion workflow](barrad-content-icons.md). Standard/shine goal sprites and idea sprites are in the three `HSM_BAR_content_*.gfx` registries.
- Kasa, Southern Deer and Wittenland banners were checked against installed EaW flags. No human hands were identified.
- Historical repairs: an unwanted Earth globe in `lesson` became a botanical study; an unsolicited fleur-de-lis on `scales` became plain book binding. Both repaired sources are shipped.
- The preceding 45 review rows and source/goal hashes are unchanged. Their comparison is enforced by the content builder; the new hashes below record this batch's reviewed revision, without silently reapproving future changes.
- Windows checks: `node tools/Build-BarradContentIcons.cjs --check` passed; `node tools/Test-BarradContentIcons.cjs` passed 16 fixture scenarios; `pwsh -NoProfile -File tools/Test-BarradArt.ps1` passed 45 asset scenarios. PNG decoding/alpha, TGA payload/alpha, references and goal shine masks were validated.

### New Source and Goal Revisions

| ID | Source PNG SHA-256 | Export TGA SHA-256 |
| --- | --- | --- |
| `HSM_BAR_art_anomalies` | `5f85434a3731f521ad993176614902337a3a5fcbead1cd5f253e5f3ea8e919ca` | `20c49e3f6d936cdf1144409bd07387a7a92db1fa3a87ec6c20d6b18f9ed9d8b0` |
| `HSM_BAR_art_artillery` | `ced96a116baeaff0e6cda9cd34bd307686dc628e11020c1ee5c25a75529549db` | `e0c4493831e6e70857dc3a207c49ac523b9273cd50d99d847ca492702948861f` |
| `HSM_BAR_art_assembly` | `2f01b87c31c55c53beed97dba8b92a28d5c2a56501496ea26537a8ac7cfc294a` | `f607b26e44fb871bf8adb0dce2a14a1f81f7bc107d938558bd8c937693138072` |
| `HSM_BAR_art_beyond` | `315f5c524e85e1282e4afd70d8fcae25febd71af99f01f3f1d9b9bf7a0198f1a` | `0d3e536928517797b9205eb37f9abbdd8ba82c77b29fc6eee170adcaff226c59` |
| `HSM_BAR_art_bridge` | `de206c7083c46eecef846d27a0be7466fe08cd520fe92795d1089c5de507dea9` | `a9ea7002b7424428dad0dbd9038c817fbe07e188de9558c4d33304cdf1f54c39` |
| `HSM_BAR_art_budget` | `eb4e33514398b68d8478a4541c63549fad46ba7611948c93a9975ccc6f6065d5` | `212ee3114cd8cf36999b5250ef430b0be69e04634fd48275f98419daeb215d96` |
| `HSM_BAR_art_chorus` | `beaff4980c729fc2297878d0522acae7fb8f5b248b91144daa7848f552ea46e3` | `34bacb43f96d77426ea14906ee1e6ad3ea8f3f0d77324d030692bd87c7144c60` |
| `HSM_BAR_art_collegium` | `d49e75fc117bc0c57a9b7110699df14c13cfc64de7447739126273be02f6b30b` | `3218ec1b97bba77eeb1b1ca74f57364017f6c1cf470c286640aa70ed739541cb` |
| `HSM_BAR_art_contact` | `a504791378002d71701a83da1c6b1eafbe64c1d9f621bb206e7f413184648f7c` | `24d81f1f71789d742939258006b6f761aac3e787c5e642e8c9490b1c0e34944a` |
| `HSM_BAR_art_deer` | `1662ce43b0046a18dba1218da111281e64f1e1e82589eae0ef1525ea6471f512` | `20c2ff1a6f3a23a76208c53a9792f803fb33f56af890a68cd4fadf00c1ff0c5c` |
| `HSM_BAR_art_field` | `1aa397aeade55bbeaabb5e1c9fb78ff5f81b7bed3dd9e2819374d86493615a5d` | `7daae459436f3a28de79aef09b18091c0d807534df2f64e70b8120fdd8dd0ec1` |
| `HSM_BAR_art_friendship` | `3e77ad14a0e46109211717640252b8161fc6f41fee4497ff1d7fbe8c6efc6370` | `b367d34ec8114e7347d6edfde92840888b833e8ed05c0b58909c0738b4edaf91` |
| `HSM_BAR_art_grid` | `8fe2c923bc6e0f6a040946f47321067eb748cf5ad633300b8a930a92a99bf08d` | `90097d3335da6ef37174d20033f4f6a5f851a81505196afdb5bb170dba28e2e7` |
| `HSM_BAR_art_guard` | `5ef3da7f5afde207ea772be0782148da678284b973d8d6a9fa1b2c7b90734468` | `8bde0e2b5fb48d30f4f345d17b30a24ce54ae0ec6b703d1c3ccba8f630eefa14` |
| `HSM_BAR_art_hospital` | `90ee6aa7983da7e7ddeb7fbb226297ab69c0ec03b070b77796d9331f77c472f9` | `2bd89dcc7489d76d259f791f5e44930a2caed37b2e541edfd1f4b79563aa17a9` |
| `HSM_BAR_art_housing` | `84ce54c842c34b9ad4f485852b514ad7edd4abbd2578573cac2e3413ef66b117` | `6f587b222880f68b487987aa8ae7fa5a6605386334b341653799389aa3a32921` |
| `HSM_BAR_art_inspection` | `67be84eaf56f4b489ff8aba03405f432e62972d4efa3fb3e9fae64914de82456` | `beeecdf113f3a274c7df769138dbe127193720eff4355f67cec863410ebab4a1` |
| `HSM_BAR_art_kasa` | `af638d6f1023c1866cc0227fc7f3daeaa3a53cb4638153b1e899fc8603ab2381` | `735be41da9dc77510ad553a36e8bc418e7c8b3e4ce651ad5cd2987e7cd29d09f` |
| `HSM_BAR_art_last_minute` | `2d6440277e2634c624ccd695b8a63b8e3dca4b1469d1333bd6a90fd9fa46a7cc` | `c3052475986312931bfa2e1b041971e3308b9bb92a4a14a4b0989795683c65cc` |
| `HSM_BAR_art_lesson` | `c62a3c722822d3774cc43c787bd9ce321cfb7efeb8326781705a120662d1a424` | `333670e24f927725a0c6372544f0790c054b12aaf276e263c948df412319979d` |
| `HSM_BAR_art_manufactory` | `9f3a92df3fce69c79e1f0c0a6769149ed4a5a6480b47fe2e52a2ba2e3c95f64e` | `a6e77e5850b61ebef6899564659347b5f95ac2c78ad36ef19b69d5f1e6ab002c` |
| `HSM_BAR_art_memorial` | `781903c6678b8d13e76f55ba439621aa0ea3b79d655e68085b32173a0ce7d3b6` | `6d5559abd09f8e0b2d127149d476ad8786afaea133d6cd12e913e1e3b5cff5d3` |
| `HSM_BAR_art_mortal_life` | `b33a71366ee2e4648d74c1433431459cb56389785621ef060994f4b060df9828` | `e8d9e23dbaab3d5a464d8ebbbfdeef9ec449b064e0b66cb86fdf45b4b3950f0d` |
| `HSM_BAR_art_peer_review` | `2b0817cfe789fd3b081b3131e63ad505dcc0bb0e4812e21bec7559733f1eebf4` | `94fde912fbe37a856e3f0900a3057315da3d2f565dbf81a4865e2afd8ee3832f` |
| `HSM_BAR_art_precision` | `3229e439bdf8dfd7f82c9530888dda89dc9c40f241af67aa007d4cea5f58ce21` | `23d7dc407b560fce08045b117e550fc8079f61efd27353d404ceec480fb81581` |
| `HSM_BAR_art_prosthesis` | `408986415a1e0071bead57c8bbc6f1008021610c21c258f471bd4c7ed9c3f651` | `17bb2ece7f8c7bd349c661cfed27ca54a78e2563ab0cc37033c08c8312fc5a50` |
| `HSM_BAR_art_refugees` | `d3e8adfbdeff9e1559d4946213c60b1821672aba5a40933c1b479f9cc8da06f5` | `c0b630fea5be943c114cf7f1f43002f2dfa816270ff53e2ec9ca9ef41031fc0d` |
| `HSM_BAR_art_registry` | `d0df2802aa17e5de38ee79d669e7633e6cc4b1721bcadf3ab6926acfe49dc58e` | `2645392a910256b1d1ed54214d5e887a9e0f15f85de5cf884537ead1dba03ee5` |
| `HSM_BAR_art_representation` | `6d70d89c46043d9e7d4884d4f82b41f24a0e8ff2e774962f1c9a59aaf0eef346` | `7ab7547d4d46991f51b29472629d04efb130d2332e8f1602b210c7577691796a` |
| `HSM_BAR_art_republic` | `a3678be6ee29ef18f0f4432b9ce6f8c8e0eb2bc0d72765235ca3f2ec72caea87` | `996e2ef0696d9dbede28568c967d4531dd91dc84c71639110f34adb54b451588` |
| `HSM_BAR_art_rift` | `d18d9f5b8305018f03ad2811e5a4b30c9c81b1c2ebca1b6ea918a307a753a359` | `99d9a2cd48188bcc6ef34ccc72f8f28d5f9d9b547e755fc76691e5db01caf4b4` |
| `HSM_BAR_art_ritual_brake` | `142ee5e6c40fe3e2717f546c83e72c64d94f2b9548afe528fe41c5d7f4192320` | `51fac97dd49e345275056a3c0368f6b6cc3976ab3bbccd0c23af5b47e1586445` |
| `HSM_BAR_art_scales` | `ccfb6da9ebf6d3e639845fdd26b9c9d40a0508943c4056df00057a1990fd703a` | `00130e53fd2b2691e275358ba6866edf8456902ada60956b949de5b1042097af` |
| `HSM_BAR_art_teacher` | `e7d9ae666570628d0a239bf09825656701b05aab484dd623da6db2d59ed59b84` | `bae153cdf46c744075aa1ea91756827b913cecb035579a1ec2ed9948c977911f` |
| `HSM_BAR_art_tutelage` | `08be4bca77ecb2b6d913faaa557ae14e86772d0a2c7cd755b932cbb9b5e2cfd3` | `c01fd028f325ad428210a918b3e5caefd0714b61b7ba6b44dcb92f536383b422` |
| `HSM_BAR_art_ward` | `e62bcbb805795ec5aec084c04bb0412bbac9d05dc7a46257d9b5d47a07002006` | `d65ba02d79546feae725e5906de2b619dc5b6428bd5d9b095aa28b61414ffa7a` |
| `HSM_BAR_art_water` | `638ad702e4650bbd116537aa5ee976c59f4f16f94a621ecea9888c5a2edca71b` | `3e61f54f78678f2d5ec265442c4fea173194964aa144266edaa39c7a01afa193` |
| `HSM_BAR_art_wittenland` | `3abcb94696fb6f537da9982738077614ef10cc75e5526e6ad632ec4d4a7013df` | `9eec18cbd7577d2919b5d4197afdcd9e20a942697fd20ccfea1925671bdeee3d` |

### Idea Export Revisions

Paths are relative to `mod/HoISubmod/gfx/interface`. The matching source PNG revision appears in the historical or new source table above.

| Texture | TGA SHA-256 |
| --- | --- |
| `ideas/HSM_BAR_art_anomalies.tga` | `3f4aa8f866da654916e8d3e9cc466fb3c5d05dea26ddf2cb65cdef58525a37da` |
| `ideas/HSM_BAR_art_artillery.tga` | `269efc242fde09cb42c7806b66f3635ade0f5a59e604168d13085c4c7a287bd2` |
| `ideas/HSM_BAR_art_beyond.tga` | `5240186b2a8f19251a2f5279baf512bc9b4367748b89880a8ce7b8db80644b01` |
| `ideas/HSM_BAR_art_bridge.tga` | `1e382480a62bc4c61db1fa377f7cf62a9c5e615fedd34f2839500d1c86dbfde4` |
| `ideas/HSM_BAR_art_chorus.tga` | `2329c3f24f37f25cbf03dc5f7a54bd19b657cf29148d3e2c86ec91b1280690c3` |
| `ideas/HSM_BAR_art_collegium.tga` | `fac989ad5df34d126ee4f0a6c95e9c87f2c0604a35a7fca1046632b398819e65` |
| `ideas/HSM_BAR_art_grid.tga` | `22017f0134ff5f448ec8aa08af4666eb8850cdad44a41cf2057b9a07a281e5ca` |
| `ideas/HSM_BAR_art_guard.tga` | `125ddabde5d420c45729b6044430faa673c0bb7ef85b853321e16b5517f9a709` |
| `ideas/HSM_BAR_art_hospital.tga` | `c9e7c6d04f6d0a301dd8afe8bb362ea3550b3775da49c998f1221e6395249b17` |
| `ideas/HSM_BAR_art_last_minute.tga` | `a0daacc9b746bffb3387b541f8d641805d2fa23bea71a0b84fc1539af6c8d9ac` |
| `ideas/HSM_BAR_art_manufactory.tga` | `2239b5bedeb3a934d4ed1a670e867971c824aef96be26dcbc20df1a0f99a3ec9` |
| `ideas/HSM_BAR_art_peer_review.tga` | `b589e0e3b6cc7e2436d98a4557bc9fbe60dc1c64b1a009a3e67c791ab99529e7` |
| `ideas/HSM_BAR_art_refugees.tga` | `fc814b42a3bd18086e26240e2ed629196978cd3aace0f13b8af78c5daf687925` |
| `ideas/HSM_BAR_art_republic.tga` | `4ee6956bed1e7adf2116a1227769ac0e0c9b9044a19c93bd078c852b7991f60a` |
| `ideas/HSM_BAR_art_rift.tga` | `605af7fdf6824055f98a84438c57c8b80dfd2f342113922df4c8338422ae7723` |
| `ideas/HSM_BAR_art_ritual_brake.tga` | `26a6396d63f664590f9457832e70f7dd1d3f0a5c7e1d1e109f145fed44dc20ec` |
| `ideas/HSM_BAR_art_tutelage.tga` | `3e1205a3b74dc506859921f8ec3599269d9d51f84fa96798ef99a91d0ccbfb35` |
| `ideas/HSM_BAR_art_ward.tga` | `5ba6eeabe53319c981dda69f6baba071e672ef9cc1eba824cc999cc062f51fbe` |
| `ideas/HSM_BAR_dir_activation.tga` | `c335de6d05402db2452eaf4a3749c835ca971a7e6273ed8eb2d18081adba14b8` |
| `ideas/HSM_BAR_dir_agency.tga` | `63425b63f088fd99e63f05a0ad903ad12a4249747e3fbe4090365605af68dac2` |
| `ideas/HSM_BAR_dir_custody_law.tga` | `35a8e7dfda2915871f1e2c5625d42b577354d22ec78c8b32596a0d21cc8e3fa1` |
| `ideas/HSM_BAR_dir_evidence.tga` | `f4725eccec53b7d81e12f3b9c3d7395eb884a08f2ced364208d620ccccac9f3d` |
| `ideas/HSM_BAR_dir_normalization.tga` | `13cb0c13aed12b7355243cff9aa990f3ac47d2e0068a1e0d6b823fd66d8b4e65` |
| `ideas/HSM_BAR_dir_remains.tga` | `3be9214b0d7c6f089ac8834ed6bfd1e6308ebddb921bac53b3523a8bfa3f27b5` |
| `ideas/HSM_BAR_dir_seal_labs.tga` | `9aa6551807bf2056d6d2f7812f28ad378a063842f44a743155f0013b34e6ccf1` |
| `ideas/HSM_BAR_dir_storage.tga` | `bc6f4385088682f02b237c63130459fa4834cd1abaecf9f79ded062beea849ad` |
| `ideas/HSM_BAR_dir_training.tga` | `2abf3a373e2cac49e0736c55817e20550de2b8c963bc3a29da6445819ceff384` |
| `ideas/HSM_BAR_dir_watchmen.tga` | `7db46bb3a306222db0d57d9478c050ba299cae05c923bb9e5723e3419cd7eaf0` |
| `ideas/HSM_BAR_dir_world.tga` | `6d0fd1f8f60da055edb3cf1fd7e01b589bf75c1a8e2ac881c19e94657a685dc3` |

