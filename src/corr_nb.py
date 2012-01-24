"""
Setup and unique functionality for the narrow-band correlator modes. Here narrowband consists of two filterbanks, with the first one doing a coarse channelisation and the second further channelising one of those channels. As used by KAT-7's narrowband mode.
"""
"""
Revisions:
2011-07-07  PVP  Initial revision.
"""
import numpy, struct, construct, corr_functions, snap

def bin2fp(bits, m = 8, e = 7):
    if m > 32:
        raise RuntimeError('Unsupported fixed format: %i.%i' % (m,e))
    shift = 32 - m
    bits = bits << shift
    m = m + shift
    e = e + shift
    return float(numpy.int32(bits)) / (2**e)

# f-engine status
register_fengine_fstatus = construct.BitStruct('fstatus0',
    construct.BitField('coarse_bits', 5),       # 27 - 31
    construct.BitField('fine_bits', 5),         # 22 - 26
    construct.BitField('sync_val', 2),          # 20 - 21
    construct.Padding(2),                       # 18 - 19
    construct.Flag('xaui_lnkdn'),               # 17
    construct.Flag('xaui_over'),                # 16
    construct.Padding(9),                       # 7 - 15
    construct.Flag('clk_err'),                  # 6
    construct.Flag('adc_disabled'),             # 5
    construct.Flag('ct_error'),                 # 4
    construct.Flag('adc_overrange'),            # 3
    construct.Flag('fine_fft_overrange'),       # 2
    construct.Flag('coarse_fft_overrange'),     # 1
    construct.Flag('quant_overrange'))          # 0

# f-engine coarse control
register_fengine_coarse_control = construct.BitStruct('coarse_ctrl',
    construct.Padding(32 - 10 - 10 - 1),        # 21 - 31
    construct.Flag('mixer_select'),             # 20
    construct.BitField('channel_select', 10),   # 10 - 19
    construct.BitField('fft_shift', 10))        # 0 - 9

# f-engine fine control
register_fengine_fine_control = construct.BitStruct('fine_ctrl',
    construct.Padding(32 - 13 - 2 - 1),         # 16 - 31
    construct.Flag('skip_window'),              # 15
    construct.BitField('fine_debug_select', 2), # 13 - 14
    construct.BitField('fft_shift', 13))        # 0 - 12

# f-engine control
register_fengine_control = construct.BitStruct('control',
    construct.Padding(4),                       # 28 - 31
    construct.BitField('debug_snap_select', 3), # 25 - 27
    construct.Flag('debug_pol_select'),         # 24
    construct.Padding(2),                       # 22 - 23
    construct.Flag('fine_chan_tvg_post'),       # 21
    construct.Flag('adc_tvg'),                  # 20
    construct.Flag('fdfs_tvg'),                 # 19
    construct.Flag('packetiser_tvg'),           # 18
    construct.Flag('ct_tvg'),                   # 17
    construct.Flag('tvg_en'),                   # 16
    construct.Padding(4),                       # 12 - 15
    construct.Flag('flasher_en'),               # 11
    construct.Flag('adc_protect_disable'),      # 10
    construct.Flag('gbe_enable'),               # 9
    construct.Flag('gbe_rst'),                  # 8
    construct.Padding(4),                       # 4 - 7
    construct.Flag('clr_status'),               # 3
    construct.Flag('arm'),                      # 2
    construct.Flag('man_sync'),                 # 1
    construct.Flag('sys_rst'))                  # 0

# x-engine control
register_xengine_control = construct.BitStruct('ctrl',
    construct.Padding(32 - 16 - 1),     # 17 - 31
    construct.Flag('gbe_out_enable'),   # 16
    construct.Flag('gbe_rst'),          # 15
    construct.Padding(15 - 12 - 1),     # 13 - 14
    construct.Flag('flasher_en'),       # 12
    construct.Flag('gbe_out_rst'),      # 11
    construct.Flag('loopback_mux_rst'), # 10
    construct.Flag('gbe_enable'),       # 9
    construct.Flag('cnt_rst'),          # 8
    construct.Flag('clr_status'),       # 7
    construct.Padding(7 - 0 - 1),       # 1 - 6
    construct.Flag('vacc_rst'))         # 0

# x-engine status
register_xengine_status = construct.BitStruct('xstatus0',
    construct.Padding(32 - 18 - 1),     # 19 - 31
    construct.Flag('gbe_lnkdn'),        # 18
    construct.Flag('xeng_err'),         # 17
    construct.Padding(17 - 5 - 1),      # 6 - 16
    construct.Flag('vacc_err'),         # 5
    construct.Flag('rx_bad_pkt'),       # 4
    construct.Flag('rx_bad_frame'),     # 3
    construct.Flag('tx_over'),          # 2
    construct.Flag('pkt_reord_err'),    # 1
    construct.Flag('pack_err'))         # 0

# x-engine tvg control
register_xengine_tvg_sel = construct.BitStruct('tvg_sel',
    construct.Padding(32 - 1 - 2 - 2 - 6),  # 11 - 31
    construct.BitField("vacc_tvg_sel", 6),  # 5 - 10
    construct.BitField("xeng_tvg_sel", 2),  # 3 - 4
    construct.BitField("descr_tvg_sel", 2), # 1 - 2
    construct.Flag('xaui_tvg_sel'))         # 0

# the snap_rx block on the x-engine
snap_xengine_rx = construct.BitStruct("snap_rx0",
    construct.Padding(128 - 64 - 16 - 5 - 28 - 15), 
    construct.BitField("ant", 15), 
    construct.BitField("mcnt", 28), 
    construct.Flag("loop_ack"),
    construct.Flag("gbe_ack"),
    construct.Flag("valid"),
    construct.Flag("eof"),
    construct.Flag("flag"),
    construct.BitField("ip_addr", 16),
    construct.BitField("data", 64))

# the raw gbe rx snap block on the x-engine
snap_xengine_gbe_rx = construct.BitStruct("snap_gbe_rx0",
    construct.Padding(128 - 64 - 32 - 7),
    construct.Flag("led_up"),
    construct.Flag("led_rx"),
    construct.Flag("eof"),
    construct.Flag("bad_frame"),
    construct.Flag("overflow"),
    construct.Flag("valid"),
    construct.Flag("ack"),
    construct.BitField("ip_addr", 32),
    construct.BitField("data", 64))

# the snap block immediately after the x-engine
snap_xengine_vacc = construct.BitStruct("snap_vacc0", construct.BitField("data", 32))

# the xaui snap block on the f-engine - this is just after packetisation
snap_fengine_xaui = construct.BitStruct("snap_xaui",
    construct.Padding(128 - 1 - 3 - 1 - 1 - 3 - 64),
    construct.Flag("link_down"),
    construct.Padding(3),
    construct.Flag("mrst"),
    construct.Padding(1),
    construct.Flag("eof"),
    construct.Flag("sync"),
    construct.Flag("hdr_valid"),
    construct.BitField("data", 64))

def fft_shift_coarse_set_all(correlator, shift = -1):
    """
    Set the per-stage shift for the coarse channelisation FFT on all correlator f-engines.
    """    
    if shift < 0:
        shift = correlator.config['fft_shift_coarse']
    corr_functions.write_masked_register(correlator.ffpgas, register_fengine_coarse_control, fft_shift = shift)
    correlator.syslogger.info('Set coarse FFT shift patterns on all F-engines to 0x%x.' % shift)

def fft_shift_fine_set_all(correlator, shift = -1):
    """
    Set the per-stage shift for the fine channelisation FFT on all correlator f-engines.
    """
    if shift < 0:
        shift = correlator.config['fft_shift_fine']
    corr_functions.write_masked_register(correlator.ffpgas, register_fengine_fine_control, fft_shift = shift)
    correlator.syslogger.info('Set fine FFT shift patterns on all F-engines to 0x%x.' % shift)

def fft_shift_get_all(correlator):
    """
    Get the current FFT shift settings, coarse and fine, for all correlator f-engines.
    """
    rv = {}
    for in_n, ant_str in enumerate(correlator.config._get_ant_mapping_list()):
        ffpga_n, xfpga_n, fxaui_n, xxaui_n, feng_input = correlator.get_ant_str_location(ant_str)
        coarse_ctrl = corr_functions.read_masked_register([correlator.ffpgas[ffpga_n]], register_fengine_coarse_control)
        fine_ctrl = corr_functions.read_masked_register([correlator.ffpgas[ffpga_n]], register_fengine_fine_control)
        rv[ant_str] = [coarse_ctrl[0]['fft_shift'], fine_ctrl[0]['fft_shift']]
    return rv

def feng_status_get(c, ant_str):
    """
    Reads and decodes the status register for a given antenna. Adds some other bits 'n pieces relating to Fengine status.
    """
    ffpga_n, xfpga_n, fxaui_n, xxaui_n, feng_input = c.get_ant_str_location(ant_str)
    rv = corr_functions.read_masked_register([c.ffpgas[ffpga_n]], register_fengine_fstatus, names = ['fstatus%i' % feng_input])[0]
    if rv['xaui_lnkdn'] or rv['xaui_over'] or rv['clk_err'] or rv['ct_error'] or rv['fine_fft_overrange'] or rv['coarse_fft_overrange']:
        rv['lru_state']='fail'
    elif rv['adc_overrange']:
        rv['lru_state']='warning'
    else:
        rv['lru_state']='ok'
    return rv

def coarse_channel_select(c, mixer_sel = -1, channel_sel = -1):
    """
    Select a coarse channel to process further with the fine FFT.
    """
    if mixer_sel > -1:
        corr_functions.write_masked_register(c.ffpgas, register_fengine_coarse_control, mixer_select = True if mixer_sel == 1 else False)
    if channel_sel > -1:
        corr_functions.write_masked_register(c.ffpgas, register_fengine_coarse_control, channel_select = channel_sel)

"""
SNAP blocks in the narrowband system.
"""

snap_adc = 'adc_snap'
snap_debug = 'snap_debug'

snap_fengine_adc = construct.BitStruct(snap_adc,
    construct.BitField("d0_0", 8),
    construct.BitField("d0_1", 8),
    construct.BitField("d0_2", 8),
    construct.BitField("d0_3", 8),
    construct.BitField("d1_0", 8),
    construct.BitField("d1_1", 8),
    construct.BitField("d1_2", 8),
    construct.BitField("d1_3", 8))
def get_snap_adc(c, fpgas = []):
    """
    Read raw samples from the ADC snap block.
    2 pols, each one 4 parallel samples f8.7. So 64-bits total.
    """
    raw = snap.snapshots_get(fpgas = fpgas, dev_names = snap_adc, wait_period = 3)
    repeater = construct.GreedyRepeater(snap_fengine_adc) 
    rv = []
    for index, d in enumerate(raw['data']):
        upd = repeater.parse(d)
        data = [[],[]]
        for ctr in range(0, len(upd)):
            for pol in range(0,2):
                for sample in range(0,4):
                    uf = upd[ctr]['d%i_%i' % (pol,sample)]
                    f87 = bin2fp(uf)
                    data[pol].append(f87)
        v = {'fpga_index': index, 'data': data}
        rv.append(v)
    return rv

snap_fengine_debug_coarse_fft = construct.BitStruct(snap_debug,
    construct.BitField("d0_r", 16),
    construct.BitField("d0_i", 16),
    construct.BitField("d1_r", 16),
    construct.BitField("d1_i", 16),
    construct.BitField("d2_r", 16),
    construct.BitField("d2_i", 16),
    construct.BitField("d3_r", 16),
    construct.BitField("d3_i", 16))
def get_snap_coarse_fft(c, fpgas = [], pol = 0):
    """
    Read and return data from the coarse FFT.
    """
    if len(fpgas) == 0:
        fpgas = c.ffpgas
    corr_functions.write_masked_register(fpgas, register_fengine_control, debug_snap_select = 0, debug_pol_select = pol)
    snap_data = snap.snapshots_get(fpgas = fpgas, dev_names = snap_debug, wait_period = 3)
    rd = []
    for ctr in range(0, len(snap_data['data'])):
        d = snap_data['data'][ctr]
        repeater = construct.GreedyRepeater(snap_fengine_debug_coarse_fft)
        up = repeater.parse(d)
        coarsed = []
        for a in up:
            for b in range(0,4):
                num = bin2fp(a['d%i_r'%b], 16, 15) + (1j * bin2fp(a['d%i_i'%b], 16, 15))
                coarsed.append(num)
        rd.append(coarsed)
    return rd

snap_fengine_debug_fine_fft = construct.BitStruct(snap_debug,
    construct.Padding(128 - 72),
    construct.BitField("p0_r", 18),
    construct.BitField("p0_i", 18),
    construct.BitField("p1_r", 18),
    construct.BitField("p1_i", 18))
def get_snap_fine(fpgas, bitstruct):
    snap_data = snap.snapshots_get(fpgas = fpgas, dev_names = snap_debug, wait_period = 3, man_trig = 1)
    rd = []
    for ctr in range(0, len(snap_data['data'])):
        d = snap_data['data'][ctr]
        repeater = construct.GreedyRepeater(bitstruct)
        up = repeater.parse(d)
        fdata_p0 = []
        fdata_p1 = []
        for a in up:
            p0c = bin2fp(a['p0_r'], 18, 17) + (1j * bin2fp(a['p0_i'], 18, 17))
            p1c = bin2fp(a['p1_r'], 18, 17) + (1j * bin2fp(a['p1_i'], 18, 17))
            fdata_p0.append(p0c)
            fdata_p1.append(p1c)
        rd.append([fdata_p0, fdata_p1])
    return rd
def get_snap_fine_fft(c, fpgas = []):
    """
    Read and return data from the fine FFT.
    """
    if len(fpgas) == 0:
        fpgas = c.ffpgas
    corr_functions.write_masked_register(fpgas, register_fengine_control, debug_snap_select = 1)
    corr_functions.write_masked_register(fpgas, register_fengine_fine_control, fine_debug_select = 2)
    return get_snap_fine(fpgas, snap_fengine_debug_fine_fft)
def get_snap_fine_buffer(c, fpgas = []):
    """
    Read and return data from the buffer before the fine FFT.
    """
    if len(fpgas) == 0:
        fpgas = c.ffpgas
    corr_functions.write_masked_register(fpgas, register_fengine_control, debug_snap_select = 1)
    corr_functions.write_masked_register(fpgas, register_fengine_fine_control, fine_debug_select = 0)
    return get_snap_fine(fpgas, snap_fengine_debug_fine_fft)
def get_snap_fine_window(c, fpgas = []):
    """
    Read and return data from the fine FFT.
    """
    if len(fpgas) == 0:
        fpgas = c.ffpgas
    corr_functions.write_masked_register(fpgas, register_fengine_control, debug_snap_select = 1)
    corr_functions.write_masked_register(fpgas, register_fengine_fine_control, fine_debug_select = 1)
    return get_snap_fine(fpgas, snap_fengine_debug_fine_fft)

def DONE_get_fine_fft_snap(correlator):
    # interpret the ant_string
    (ffpga_n, xfpga_n, fxaui_n, xxaui_n, feng_input) = correlator.get_ant_str_location(ant_str)
    # select the data from the fine fft
    fpga = correlator.ffpgas[ffpga_n]
    corr_functions.write_masked_register([fpga], register_fengine_fine_control, snap_data_select = 0, quant_snap_select = 0)
    data = fpga.snapshot_get(dev_name = fine_snap_name, man_trig = False, man_valid = False, wait_period = 3, offset = -1, circular_capture = False, get_extra_val = False)
    unpacked = list(struct.unpack('>%iI' % (len(data['data']) / 4), data['data']))
    # re-arrange the data sensibly - for FFT data it's complex 16.15 fixed point signed data
    # make the actual complex numbers
    d  = []
    for ctr in range(0, len(unpacked)):
        num = unpacked[ctr]
        numR = numpy.int16(num >> 16)
        numI = numpy.int16(num & 0x0000ffff)
        d.append(numR + (1j * numI))
    return d

def DONE_get_ct_snap(correlator, offset = -1):
    corr_functions.write_masked_register(correlator.ffpgas, register_fengine_fine_control, quant_snap_select = 2)
    raw = snap.snapshots_get(correlator.ffpgas, dev_names = fine_snap_name, man_trig = False, man_valid = False, wait_period = 3, offset = offset, circular_capture = False)
    chan_values = []
    for index, d in enumerate(raw['data']):
        up = list(struct.unpack('>%iI' % (len(d) / 4), d))
        values = [[], []]
        for value in up:
            # two freq channel values for the same freq-channel, both pols
            # will have to use the offset to get multiple freq channels
            p00 = value >> 24
            p10 = (value >> 16) & 0xff
            p01 = (value >> 8) & 0xff
            p11 = value & 0xff
            def extract8bit(v8):
                r = (v8 & ((2**8) - (2**4))) >> 4
                i = (v8 & ((2**4) - (2**0)))
                return r + (1j * i)
            values[0].append(value >> 24)
            values[0].append((value >> 8) & 0xff)
            values[1].append((value >> 16) & 0xff)
            values[1].append(value & 0xff)
        chan_values.append({'fpga_index': index, 'data': values})
    return chan_values
# end
