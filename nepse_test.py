import pandas as pd
import time
import random
from datetime import timedelta
import requests


xsrf_token = '6f121535-5ab4-4040-80a7-c0df3cdcb809'
host_session_id =  'TVRJPS0xNmFmNGZlMi1jZTk4LTQ2Y2MtYTllMC0xZmNlMWJmYjk0ZWM='

cookies = {
    '_rid': 'eyJlbmMiOiJBMTI4R0NNIiwiYWxnIjoiZGlyIn0..3GUxFzhqmUj-Ik_4.DXu4ycHcjAQ4kczZdMq13b7LRrah4Mr3pPeNITXrGMRU2GpaczP_EJRb2eBLYHd2G_7rEqTsmcSGcChHDGs43ys6kAaw6phGqecZXsDGH83Hv-MR5JJYHnduiEUmq1j3Hz__8z03JFpQ6MX5WSrqvLVKyt097d7Ug7w5tiYR9bMiZbQVN1Dt-HlWutSmnfKoQ_R-eL8tUh4EF7upNo357a_pTBEVPYPKwEyI3AsJBPxQCNeBWY3-l0V4UlASHxDBvDDIPmeSf0KUNTp0TdbFeIO_rOA8py5PtkbNDSah8zpSiLic_mgCHic-lYqOzfbVrPYk9A2Z_s1k5Lnz3uymaj_XKFaItAMN4PaiuDIv1Ve_d7zrf9aPc9CBx7x4vNZ1IYlUr59yl5IhXsso-Lr96wvkg2UyyGhY6k6cKKN2A9untci2ry_K2hs3RJH2E85RetKfPQ04rvZCdZpSLJnBJQax1LG8CkEX-zQlwZn6z7vFyeMyBQhHCMdXCimIUL5I_YVjgvWCeMoRTg8rIHi6d-kSXKw7LCFoAoTnpzIjukrY6ZWck1OKkK4MkCuHBMWSZL5yJzoEv7hheq8DJy4XJ9nHtErBr8PtWdjToiqTU8FZ85WXgWYaKQz6a4jw6hcpIM38pm6vdEV8dGwPHJF6mogDW91FKAEMUHq3yHyz9Fbre-PwXom4J0CPvjz-WWHPNe2CQBrTLY2f66sPlHP-fYFRu5naz4FEHtP5I1ChIsDghlMevyISUcIanUqK_aA9e2XD3ioQtItomjHhWSzWEuZJ8tyCQNDMIGfvchelvOl95KID7PPVQfqdVtNociuxeLywPXv6VcFF02AEc46okrrrMMGHQq8tKwqSFOOlsCGh27OpWWTA7dK6OZ94voWfDFSrx3TNe8e2bUWNLsdxMAuxnI_5DHpAkuPC3XZFQKeL_o_jI1ervXYhjyDLVXYbVJWnkGlEYNQgjpXweOQ1axCGHMGFLYM8wCTf5iF9QoFL4sPDyeQKoTn_NvaIaHDhjYn7XRdM0b5JzFie-K_BZEEWonhG9jdv2l3OTk6ZHoyHAic4ICQLhXXNwUm7NAbBL9_OWk06oDKIFw5FXmWsCsICpgsbyxCCYedTQtHS_pKJ40LoH3V_hHX9SmoElteRw8BYnWycDYGOyNcrVmJFXxEhSOt1cIjdHX55F0RhGUxpuOQeUjQNt_UzbpZyLLjuGTORMfkEFTWpH2Vr1pHkctoGzKqmIQ5KJy42D6Nh3XBnECb_ym7D6J3y1Rjw7z-pegb_smjlW0fbRsxDqewoRzJ9vuiwZMKygrTQHHFTYVyAhRWLkG3W7_JWmUy8I4h7hvg4rOw3lZxWZnwkLG4uq_AT9aV6mOeXF8_Wdz0im8JMKClS9a5BE_OwPiyfL0oU5MUmgxs6haRiIaiuDMkP7J23jwxeOjoQmnzPV1iiXos-bUwY6wd0-HqYxmlsa7de9njkw0SNUryuUwQD3z-ba0WSlcVoKXJLuUXWSMFYMEkaVXfM0mKN_wE4Y5Zx4P_SzPDxdzcYCOFNLuMPyvYsu5HO7hNQVWb57jHdL8zbrdfIJaCIFCwnUe21uEEkeGeTmE_DbjyTKkgicPg_dPzU1I6qlG4l3PB3oHFlmoD2-cCMv7TWK37CupF-cB_NwgZngC2616VMGcpA5-gYBuyA2JShnaTVdbVo3ZmH0ueYcWAshvlEod446boBCjXtaG2LKhXE9uhP6-3ZD3t1IGSA7PNVeROnKLLd6lEluFfQylLOmb2YjR7nS3ebLvirWDA31JahGd56hxbg_mOsox-ejHvOyVlveyi1jdksu4i4wTmhWZ9FvD8I7sCZUwkXw0AAzVYAx8r9WSGT-0-wrSrgAa1K4Tk29duKVQY_V-2H8LhWFw1UqW88RZxt6q-gkQRqE_NzIgqUC3K_23xIASSZvvGWiyKZTa3o3BF9EW2DXJPFJnrN2Hz1A8etD15e67cCK-ZyPlxE2ZemlYuweTkdCGRd35DrNOB_ACAsDD4pqWB3O4JckX7NDQ8GEysERcDdoz5Szj6CV3_MirggbAP0yMntPIwHCc9PV3eO-6K96z_eCQTFuiWCWkS7trZoB5hv_yhGLhI.nH13WeesY4MsQw4HUzAV9Q',
    '_aid': 'eyJlbmMiOiJBMTI4R0NNIiwiYWxnIjoiZGlyIn0..I-wBogwVCv5cTBY2.Wm7GLaFIlbKFn5S8WWKg6cbwmB5iB_Wv2u-VPk1ptiuJJvHjUFm0ByLW4Jr3ey1TmvChQOspi01f997DCVVAcAhJKdiAbzEE1oX3bNe0tGIvqyhKvP0Kq6JRUAtdojT0zo2FHmffb94hmQ-5lwUIlQ1iiQimQGN7YfDWN35zssMKN_nVTfNb01anj1bppuEf5RkODaCQIZbZkrUIj4mkMlUgaHkel91VfZ59OLxjGdmpgPLiG4eLB0A4xuUlUASFpfA1OaZGhaQsYvnbZAUx-GVp-mvMrp9GUY_Bjx8Qu7VmCiOBZJXdT0DIe0wQOKEGu9IykrFKf1TtTyAlTuxea_dJIicdb2b5e9IP5UyakavXtTx69HrSsvdeL10ymJpASU1Z-37Xo5Ax-co4LUzl6XF_WjbYqaGwgl2tUVJbuady8Hs87S2-_vZ4PNTbJA18L-a3pt0rU9E-3ynXd2VV_GzfO-yoaOe9a9v3Eu8UjF9Zopvn7AdPw8UD11KZaJ3llwjcb1XtJj8SZb_khRIWbgWhJ-orPt8twhRa-bbqP-DXN1558DwwkwB_uekOqnZBH8RCDy-OCdfX5iG09I7goUJnf_uhHr_VLYe1C7AkfvEv5B1O0HEEsiXEkT3UrnKG0TqwmVgIPDcE2z0fWfevHYh-rGRoCl0DEJ_4XQ4mdmas0Ufjcxxau5NS-kayZz9hvNlLK1DCCLGmuVRvMiBBaangoDY0hbCVeEXtJdGwG5kAif5NkoQBVoXzSjMihuLrcC3AQ2hVVd_j5x4_qL8jWaYZWMRbHui3oJHBiHGnkhVdryv1nWGmMZE5KrrZpGA2wTdm9_lROen4X7jqOfincUAz1FZgmieS7QxEzpaxo-OULIcHsnoBFy0fVRNBporYWlt218x0Nx-BIgy0LtyVIKu0kgewrP41EGVWNue9PirT4GYcQtbYAgmHtLFAXPjkx4DwXfipI1e2uYZ6L_VVGFherEDBffwBRG14VK6X4jofIXiCkr6MABwvPaI3aJsHAFo0i8jtDxIKPvKJRCTa5L8RT3yFFxrFb3beRR6saZT2uPV_iQ6lEJTVrwgN1jMDWu_JHEwdbE9Uli8QP0HMOrHUTLPWZPCp_Is7Nr1Nq3eHYpMZuedE11kMz3CnTbE54e1z59MfQgb7P_wjctpoXc0YEV-LtfBUJNWGmzsLSSwXDfICT9SBnlyRg8RB6kJTBGf69dyZ1i1Ejnnd3shtooH5sAEUGKGQbZ1E10mGTzUmIQZWNSimNkIxnUHl0D89M9MnrjjOeYIxYzD_qwveArzBsar-2Sg5bfcx0jcIfbbYLBNa5utlVghicWUtHvm6mjr9vZNhMTs5_VEBNDUXtV9B9JGt53fH-TF_mltf3p6VKYzH44dHRzkQMxns3E3Fr8NYkxG4ckY96RFXWIspdL3tBPok7xGKTuAMk3wiufmCSkEcX7d1KJ9j4ozbWOkKuUW_Q7C5wHNuU9U-oOtbzbQh4FNzVBNgkw8hHTKUltV4fGWVZnI35U1klcpfWOpFl05AvCvmQXif7Fnm1rmou-AXywY6XJgJ_t2uzLV83ecF8H_taJZCH8xVzfuFVYX8--g-V0nikHZ0Kp_WTmbmB3bOycBB0Z4bFdAS3uVhFXdn7vsi64Tjq4gbEiu4n-WKFtxfEhgJwt4TC94-QmtQJyQNyI6KB9ps1vcdsKuW-HcbNpWc8gG3hf8Q3QX-u85CZClE2DnCvoochrvKyH_20nBsDMap6B4OnhgYWrjAnSkJED9XJxmLRz-GNLlFBOWnflaM_Uc4iV1CYjawmbTzezRTK40I6qx1xYotDtS7k5V--0A63_DYMZXFX6Dhf4qoHQOVVGauh2RT_gJdOfmFrOSNrtdZG4YSs2EoiktYC1jAGrd5h52kbsamnpnjH3bkwdlFTbUmmSTKbj2Wc55Rho0ItVgfp0b1lzb4pa6LIc0BNCUkn31rFt10iEcPhcn0MFRMPEPyW7fwLLU93Ya9kqKFi9lCt19xMOpPw8oUT7sMplHSxURVllpDAy5kQdRbPNRaDd0516BEnvMhGSgjwt5EwRit8Rj8UoNFIP8yGI6AXHl8GXjjdwsyRhbBkE9udD_pJHA.W8QaI6YRbosBjgso_Q8bjA',
    'XSRF-TOKEN': '6f121535-5ab4-4040-80a7-c0df3cdcb809',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'host-session-id': host_session_id,
    'membercode': '48',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://tms48.nepsetms.com.np/tms/member/search/client-search/2192120',
    'request-owner': '105675',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'x-xsrf-token':xsrf_token,
    # 'cookie': 'XSRF-TOKEN=606f5137-8d53-4d56-9f9b-c2dd619d1f25; _aid=eyJlbmMiOiJBMTI4R0NNIiwiYWxnIjoiZGlyIn0..-yDEhVeiuMkxBb0d.BPjr_eKXEvcd49Weo-AcJ7XPle00X1mMMFYvihBvTJaEnqhf7uOakLt_0wg2jMepsK9CcDmOexpQyTlTujMILfM77j69JfAm4E8K2AerRc2OFNj10iIN2sELIkXDumHZI-xNoDQDNPZzeJFNAsbVCeJgeBwcWxnujF6iA1bkM0CgCbQPhv-sjcwrtaaLd4uKgktDkQaSZCWrGu3oMUMtNa2FP-R3amOR4pjtBElNmmDpY8P_wYNrLxSst123oXVc-ib6bAqQZQHb_kr-NYUWW-aU8hiMqb7hjjaO4He7pWaI11tXNrFAevc7fNGS_hXAwNRTb_2BxI4xrsonr-fAodHjccjzIQcesMCVA3_lvA2ciVSOrM04kITMLloma7AKrwzKa-YGSwEauTi7HQUMPckZRo97i_yaf5zenc-yjYcIrXYwYWZAFV6zzOFy_RZoXWbBCLuMW04lhg8LA8S0TQRsgZMHYRxPCld3Z4NJuKmMaKzqL-Y4-ToGXgdY6PI0zeYPSjyiTt3H_DylcNXCceBdy9koo8Hy1o55YW2LW-_hdxkK9HPcyrwG_pG5-YsF8Ln2OIrEzRszeCqdpYb1gM4zAmYfv27QOR-vP0MaZLp5VyrD2NZnqsECtnq6XVRKKEt1wPLPRgnuHbeBToVv4no9D-I9qflT-3Jqm4ZFoWxbCl-mW3_278c8WtZWUgpebiRM9aT5Suyw3r7bP-kyKbAgEQ5VEPTWN9K4JvdwLDP00fUa9A34dEYnfx8oeNSNI_EvNnHGyncxVIMLUCXspeOzzVbE2DBzHe5XQklfoE7m_8PwEB3z-ZHlwCjRELigd_RDjqOyb-FPlAf2Cx4l1G4VI4PTEwXS-LuxXCMppr8FUGNUTamJRnsJDxerOZ6SZDdne5uTvlyDmzH7nViCZAGL1pCdvYvgAQGDFa1yQejJ76Jkp-re11EhwZzcgCAn93KID9o6Uql7oY8h2YoayOQSWap-dUZXsPUUuGki_Rr6uj7njUgwC4XK6FhC1YbdE2rgG19p470h2ZTc9asBkR9-Vu4bcX8oisxBZvvYChc06DWEuLvOJf2KfdtvM-RbAeC1Blhv-Tf0RiHr86DT4DTS1weqLIJdV79rK5EwfPbO_fRDdJVPFugoPXg5Br1lGJwqTwhksBsgV4kGiY4vKv268-2KjDdquaNpnl4JvZHwzj2sT2RTFYA1LVEDVYjRQQUSbJFTilcezMnyLtNGHKYKdLqEApyQ_wgm1UbfzHeDOB9DuREHcIeUNt5nwaGxZZCh4bnPycWRgObALqzFPl9109BBAd3cj48QVBB49ewRvIklhstNuTN2Wyf4UMo3u-1tIhiSW3fNcggZbJkuAfQB0X7YfW7R8-NS1S1UF361DQGFvfFJFWQSPpNSDkK7vlmlruFBypEmMLtI4JMXkCbkkNaWPI86QFe1yKYkBvuBs2eDkg3wWGmlEhBqkvrB6ajBnNhhujhfTXegzUKaphkdgu0aZ-7W778IqXAowS1ZuHpQFoge0kjXNp7ngeiVL-f_lm1ciGwehshUeHjkEd4nOYrYa7vY2jywCopEtgo1Zb9dJ18PxPzHUZgfdRG_YgHUOiEgj6B-e3ewwGvvDOfpWmm-BFOfL1Y93CZo0-g4L57Bt3vYbEirzVMMbQAvr5Z5Jiyly6uU7C6gbOl2u2xNRwKctnLqAxXQrLimdxIMN8C0NJ53sHM5xiFb518gnSZb8Ovr_adWGxe0DIqPDcHjGmLPHqDtrrKMGipKMsDYiqxHqJzFNL18TOrHGuRtQ7lixtO4NMoXEgBafA0Un1CBiDaD0ZRbBZbBRO5QYBSPNVS9eqGQye--m4p6xd-__StkSMEXk2TMJ1Ra3Cli2nIJfLjE2ibJONt-xuBmtWsZrZL_kFW-JMbZwTGxSaH0hkHotaQkqoWdxtE_1RPq3aYHNtxeF8UpwBlOdn4ABbE-3dGV-YlcUiua9zEk-UDjCOZDlKJ7i-uV-U_-2xU74oBxighnhPKFHl47MsqXgeRwOV_xQXRE55Ed7EKMlufy6Ci_3E4ZLh4BNs3x8XpC9ZJmuin68v636muCvXOHbp7ByUqxP2k31jeDTLK5xf7NPcR2vw0.YYD1DhA0J9PPO_ya9dfRSA; _rid=eyJlbmMiOiJBMTI4R0NNIiwiYWxnIjoiZGlyIn0..2nFDVXdkppIaZp4I.KwqnJl-4odfErSIHVIRbIBlM0x1eJinEuyAMfxUVdbV-tzyeR7uJIR27N-mT1GYYjco55gvMTw-tpcYzYERO6mpNvK-RdF9j5LY8oEPNUJLK9csoHpKwO7ZV-zBIzb-w0jzwn8U78VuhJ_XzJjn7ga_xrwNM0RvBvDVj_JbIlM_5rGLzy5mnnIT7e3FZGT9uIMSil4DlQ4qaG5TxLKgV1xqsKYN6ZrU3Ss4mZ7ohPOOIm6YXFVP7TaJNVzS-5TH9_TEht4sNDwuoXUxRFgecOJp-e4QMtFY6_lmD3dF8i21j-5DEFEvtbBcSH8fhJQzf-OWc3A2egcmji4omMWpZ6WzGn2qT5_E2wD_OsURFdUllb2qd6u_ONcVpOz50jrFVlWU8FzRLG2eoUeWGr3n8U-pmZRiifI714zaPYkas4xi0B395vhVmmOh8AhsVcJKaVQ-cOgbyvscdDZtNp__HYq-1q5Y0WC7PJ6i1Tgub3uyIkHHofF9A3ydqt1fAoBQ1l1L6V3AhFjxmvgd5FWVKbBL7rlwSaeS5e0Q46xrPv4iM63NUyFXCPdx2Z6Ui7RVmuvnMmXSnNY9Pww1a3YeFQs4Fd2iPoyYIWAKxjUSZfh7P6xO5leSAGbVY8wl-YjLdmZnWqbyB6vWdJFPfW9O4iIftifhBc4rxwZSiG0ZGBjgu0O0YLiur4su61Ry2YqULiIN4QWoXQ5psadxoNP3vSu1dp1YBeAaqnuF4C2V0mjfeKR9pkDibbS8Ke1N0Ez057IphE_b_ndj1n7juXpwX86sElJViakHvxoSVT5j4-AFsQrbKeu4hoS2n_mnnwb__fZvtKuE1O1xuXOzxqQFjOLwmUfjf0R9RKlnrIDyeXpnnjv5r6Qqonx36GQWcEioOPqCUq6Rvr_2JJgBD03WT8GfmzE8DlKGwMJVId_8eYICoFsI41wOQdb6enfYKUJbfZbc-BiK-JyalNhY1dbhDoVO22v-Yr5cRzkzHfHu1CLJD_X21RsXOd8LQG9KrnH0z2jq1OG3N1mdBVBvLmmdtgz01I4n2_nOI2h2h-Ep8JqKS_spHidYfG1IEKnhMiOfWkMPfMSTtoMdZVSWn8UYCwNcsXrnLSiH_aGi_fzFxCKXMWl7sClLIQz3A6dVXb264AgMYuRXuUZyIH2jNd19Qgwl_iiRx3giq3RhB6wyZFotVbi3K8c0hcCrhnOUqfy87apWJO6PR2X5iAgUOUCJUQs7LAzeaakZANeX4P_fR42YRyO6d69lDF1QO0_BqGzK_eJi9mWP1hoPocQFzM_T8E3KKugUZtlWv5C1caC2tELlyccraQm5K332uBtdQ1ty8rZLMS5i2Ir3unpWZHzk8yxmHPwbQ3n_R4VUE310AJphd7Lfu98uI6PbShpTwvlD9jWTbJfc5sbMHsaISBKYpXvAGv4HROI0v4-1jRtBTIlWmWYcslVbUnJA3iJZJazqR0_MWJ4ZTxE_x1M_YW05XtODdwQ6th7XWvIeHe77y2DgJSjo8ZaJmRKOjlmHMec4tiTNo9YFW-h16Ee6oEZ1gu6oKhUSNbPEt7SmUyJzK8TOtaOfwLau2GGXLlHz24Q8T_XmSkSuymE8uSjb0qu-InQpWjNqnk8IrY4g004wVxtQiVBWQRNumgyz7ZfMZXWzMsSSh07SwsBnNdm8nz0lIlBN_zePqhsaLFmj0kVcMHy1Ur90IZ6aAUYH5bYM4_R3N8kzjVQJr8v-QgNJIRyTORgXQSEW9Nr0o9BNJBZEYOyFoGlnGE1Nl85WcUIBN_7MUiuTWYlfngFTytTEL2zbur6d4WUmWCmzXqFPh96JVhzmpbMx3ucKf5LdlX6jZdBRICwhWviQ8eTfsun4cOJsbnxSlT_ChyhsiumAtqdFF_vHpZ2yn11d1qFrhKbqSSu4IhEtCGFTn4gEWmcL8u1wUAzRvrYh0x845_AlJ0dgw4k5fCMdftnObQFulWdzF5sJsHrnGZzA_RFxBxibeVLNkSZ4LO68qvIztnVX_A-O-U_NHtO3_6z0pE3yb88W089n_x7Golz9QriAypKTwsj0Cl42fcfXhx2LHUBaQE1e1FiWdhGkGobdbuZTiJNGJCMBou9iItCo.7WQ8DDiLwROxk7eF8Oe8aQ',
}


def get_client_ucc_and_server_id(client_code:str, cookies:str):
    while True:
        response = requests.get(
        f'https://tms48.nepsetms.com.np/tmsapi/orderbook/search-all-client/{client_code}',
        cookies=cookies,
        headers=headers,
        )
        if response.status_code == 200:
            return response.json()[0]['id'], response.json()[0]['notsUniqueClientCode'], cookies
        else:
            cookies = get_new_token()

def get_new_token():
    response = requests.post('https://tms48.nepsetms.com.np/tmsapi/authApi/authenticate/refresh', cookies=cookies, headers=headers)
    if response.status_code == 200:
        print(response.json())
        return response.cookies.get_dict()
    else:
        print(response.text)
        print(response.status_code)

def get_organization_name(server_id, cookies, df, index):
    response = requests.get(
        f'https://tms48.nepsetms.com.np/tmsapi/clientApi/clientDealer/info/{server_id}',
        cookies=cookies,
        headers=headers,
    )

    # ✅ ALWAYS return a tuple
    if response.status_code != 200:
        return None, None

    data = response.json()

    # =====================
    # CORPORATE
    # =====================
    if data['clientDealerType']['clientDealerTypeName'].lower() == 'corporate':
        df.loc[index, 'type'] = "CORPORATE"
        company = data.get('corporateDetail', {}).get('companyName')
        return company, None

    # =====================
    # INDIVIDUAL
    # =====================
    individual = data.get('clientDealerIndividual', {})
    is_minor = individual.get('isMinor')

    df.loc[index, 'type'] = "INDIVIDUAL"
    df.loc[index, 'is_minor'] = str(is_minor).title()

    if is_minor:
        return None, None

    organization = individual.get('organizationName')

    occupation_obj = individual.get('occupation')
    occupation = (
        occupation_obj.get('name')
        if occupation_obj else None
    )

    return organization, occupation



df = pd.read_csv(r"C:\Users\Prabin\Desktop\new_clients.csv")
# df = pd.read_excel(r"C:\Users\Prabin\Desktop\transaction_monitor_main.xlsx")
total_data = len(df)

cookies = get_new_token()
df['is_minor'] = ""
df['type'] = ""

start_time = time.time()
processed = 0

for index, row in df.iterrows():
    processed += 1
    client_code = str(row['client_code'])

    server_id, ucc_code, cookies = get_client_ucc_and_server_id(client_code=client_code.upper(), cookies=cookies)
    org_name, occupation = get_organization_name(cookies=cookies, server_id=server_id, df=df, index=index)

    df.loc[index, 'occupation'] = occupation
    df.loc[index, 'company'] = org_name

    # ────────────────────────────────────────
    elapsed = time.time() - start_time
    speed = processed / elapsed if elapsed > 0 else 0          # rows/sec
    remaining_rows = total_data - processed
    eta_sec = remaining_rows / speed if speed > 0 else 0
    eta = timedelta(seconds=int(eta_sec))

    print(f"{processed}/{total_data} | {speed:4.1f} rows/s | ETA: {eta} | {client_code} | {org_name} | {occupation}")
    # ────────────────────────────────────────

    time.sleep(0.5)

df.to_excel("output_new_clients.xlsx", index=False)