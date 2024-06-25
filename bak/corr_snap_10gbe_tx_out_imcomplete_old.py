#!/usr/bin/env python

'''
Grabs the contents of "snap_gbe_tx" from F engines for analysis. This is for 10GbE output F engines only. Otherwise, use the XAUI script! It doesn't have a way of asking for packets for a specific channel (TODO!) so it just keeps grabbing data, integrating and adding to the spectrum.
Assumes the correlator is already initialsed and running etc.

'''
from __future__ import absolute_import
from __future__ import print_function
import corr, time, numpy, struct, sys, logging
import six
from six.moves import range

def exit_fail():
    print('FAILURE DETECTED. Log entries:\n',c.log_handler.printMessages())
    print("Unexpected error:", sys.exc_info())
    try:
        c.disconnect_all()
    except: pass
    time.sleep(1)
    raise
    exit()

def exit_clean():
    try:
        c.disconnect_all()
    except: pass
    exit()

def feng_unpack(f, hdr_index, pkt_len):
    pkt_64bit = snap_data[f]['data'][hdr_index].data
#    pkt_mcnt = (pkt_64bit&((2**64)-(2**16)))>>16
    pkt_mcnt = (pkt_64bit) >> 16
    pkt_ant = pkt_64bit & ((2**16) - 1)
    pkt_freq = pkt_mcnt % n_chans
    exp_xeng = pkt_freq / (n_chans / n_xengs)

    sum_polQ_r = 0
    sum_polQ_i = 0
    sum_polI_r = 0
    sum_polI_i = 0

    # average the packet contents - ignore first entry (header)
    for pkt_index in range(1, pkt_len):
        pkt_64bit = snap_data[f]['data'][pkt_index].data

        for offset in range(0,64,16):
            polQ_r = (pkt_64bit & ((2**(offset+16)) - (2**(offset+12))))>>(offset+12)
            polQ_i = (pkt_64bit & ((2**(offset+12)) - (2**(offset+8))))>>(offset+8)
            polI_r = (pkt_64bit & ((2**(offset+8)) - (2**(offset+4))))>>(offset+4)
            polI_i = (pkt_64bit & ((2**(offset+4)) - (2**(offset))))>>offset
            # square each number and then sum it
            sum_polQ_r += (float(((numpy.int8(polQ_r << 4)>> 4)))/(2**binary_point))**2
            sum_polQ_i += (float(((numpy.int8(polQ_i << 4)>> 4)))/(2**binary_point))**2
            sum_polI_r += (float(((numpy.int8(polI_r << 4)>> 4)))/(2**binary_point))**2
            sum_polI_i += (float(((numpy.int8(polI_i << 4)>> 4)))/(2**binary_point))**2

    num_accs = (pkt_len-1)*(64/16)

    level_polQ_r = numpy.sqrt(float(sum_polQ_r)/ num_accs)
    level_polQ_i = numpy.sqrt(float(sum_polQ_i)/ num_accs)
    level_polI_r = numpy.sqrt(float(sum_polI_r)/ num_accs)
    level_polI_i = numpy.sqrt(float(sum_polI_i)/ num_accs)

    rms_polQ = numpy.sqrt(((level_polQ_r)**2)  +  ((level_polQ_i)**2))
    rms_polI = numpy.sqrt(((level_polI_r)**2)  +  ((level_polI_i)**2))

    if level_polQ_r < 1.0/(2**num_bits):
        ave_bits_used_Q_r = 0
    else:
        ave_bits_used_Q_r = numpy.log2(level_polQ_r*(2**binary_point))

    if level_polQ_i < 1.0/(2**num_bits):
        ave_bits_used_Q_i = 0
    else:
        ave_bits_used_Q_i = numpy.log2(level_polQ_i*(2**binary_point))

    if level_polI_r < 1.0/(2**num_bits):
        ave_bits_used_I_r = 0
    else:
        ave_bits_used_I_r = numpy.log2(level_polI_r*(2**binary_point))

    if level_polI_i < 1.0/(2**num_bits):
        ave_bits_used_I_i = 0
    else:
        ave_bits_used_I_i = numpy.log2(level_polI_i*(2**binary_point))

    return {'pkt_mcnt': pkt_mcnt,\
            'pkt_freq':pkt_freq,\
            'pkt_ant':pkt_ant,\
            'exp_xeng':exp_xeng,\
            'rms_polQ':rms_polQ,\
            'rms_polI':rms_polI,\
            'ave_bits_used_Q_r':ave_bits_used_Q_r,\
            'ave_bits_used_Q_i':ave_bits_used_Q_i,\
            'ave_bits_used_I_r':ave_bits_used_I_r,\
            'ave_bits_used_I_i':ave_bits_used_I_i}

if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('%prog [options] CONFIG_FILE')
    p.set_description(__doc__)
    p.add_option('-c', '--raw', dest='raw', action='store_true',
        help='Capture clock-for-clock data (ignore external valids on snap block).')   
    p.add_option('-t', '--man_trigger', dest='man_trigger', action='store_true',
        help='Trigger the snap block manually')   
    p.add_option('-v', '--verbose', dest='verbose', action='store_true',
        help='Be Verbose; print raw packet contents.')   
    p.add_option('-n', '--core_n', dest='core_n', type='int', default=0,
        help='Core number to decode. Default 0.')
    opts, args = p.parse_args(sys.argv[1:])
    if opts.man_trigger:
        man_trig = True
    else:
        man_trig = False

    if opts.raw:
        man_valid = True
    else:
        man_valid = False
    if args == []:
        config_file = None
    else:
        config_file = args[0]
    verbose = opts.verbose

    if not (opts.engine == 'x' or opts.engine == 'f'):
        print('Can only choose F- or X-engines. (x or f)')
        exit_fail()

try:        
    print('Connecting...', end=' ')
    c = corr.corr_functions.Correlator(config_file = config_file, log_level = logging.DEBUG if verbose else logging.INFO, connect = False)
    c.connect()
    print('done')

    if opts.man_trigger:
        man_ctrl = (1<<1)+1
    else:
        man_ctrl = 1
    if opts.raw:
        man_ctrl += (1<<2)

    print('------------------------')

    dev_name = 'snap_gbe_tx%i' % opts.core_n
    binary_point = c.config['feng_fix_pnt_pos']
    num_bits = c.config['feng_bits']
    packet_len=c.config['10gbe_pkt_len']
    n_ants = c.config['n_ants']
    n_chans = c.config['n_chans']
    n_xengs = c.config['n_xeng']
    n_ants_per_ibob=c.config['n_ants_per_xaui']

    print('Grabbing and unpacking snap data... ', end=' ')
    if opts.engine == 'x':
        servers = c.xsrvs
        snap_data = corr.snap.get_gbe_tx_snapshot_xeng(c)
    elif opts.engine == 'f':
        servers = c.fsrvs
        snap_data = corr.snap.get_gbe_tx_snapshot_feng(c)
    print('done.')

    report = dict()
    print('Analysing packets:')
    for s in snap_data:
        f = s['fpga_index']
        report[f] = dict()
        report[f]['pkt_total'] = 0
        pkt_len = 0
        prev_eof_index = -1
        report[f]['fpga_index'] = f

        for i in range(len(s['data'])):
            if opts.verbose or opts.raw:
                pkt_64bit = s['data'][i].data
                print('[%s] IDX: %i Contents: %016x' % (servers[f], i, pkt_64bit), end=' ')
                print('[%s]' % corr.corr_functions.ip2str(s['data'][i].ip_addr), end=' ')
                if s['data'][i].valid: print('[valid]', end=' ')
                if s['data'][i].link_up: print('[link up]', end=' ')
                if s['data'][i].led_tx: print('[led tx]', end=' ')
                if s['data'][i].tx_full: print('[TX buffer full]', end=' ')
                if s['data'][i].tx_over: print('[TX buffer OVERFLOW]', end=' ')
                if s['data'][i].eof: print('[EOF]', end=' ')
                print('')

            if s['data'][i].eof and not opts.raw:
                pkt_ip_str = corr.corr_functions.ip2str(s['data'][i].ip_addr)
                print('[%s] EOF at %4i. Dest: %12s. Len: %3i. ' % (servers[f], i, pkt_ip_str, i - prev_eof_index), end=' ')
                report[f]['pkt_total'] += 1
                hdr_index = prev_eof_index + 1
                pkt_len = i - prev_eof_index
                prev_eof_index = i

                if 'dest_ips' not in report[f]:
                    report[f].update({'dest_ips':{pkt_ip_str:1}})
                elif pkt_ip_str in report[f]['dest_ips']:
                    report[f]['dest_ips'][pkt_ip_str] += 1
                else:
                    report[f]['dest_ips'].update({pkt_ip_str:1})

                if pkt_len != packet_len + 1:
                    print('Malformed Fengine Packet')
                    if 'Malformed F-engine Packets' not in report[f]:
                        report[f]['Malformed F-engine Packets'] = 1
                    else:
                        report[f]['Malformed F-engine Packets'] += 1
                else:
                    feng_unpkd_pkt = feng_unpack(f, hdr_index, pkt_len)
                    
                    ## Record the reception of the packet for this antenna, with this mcnt
                    #try: mcnts[f][feng_unpkd_pkt['pkt_mcnt']][feng_unpkd_pkt['pkt_ant']]=i
                    #except: 
                    #    mcnts[f][feng_unpkd_pkt['pkt_mcnt']]=numpy.zeros(n_ants,numpy.int)
                    #    mcnts[f][feng_unpkd_pkt['pkt_mcnt']][feng_unpkd_pkt['pkt_ant']]=i
                    #print mcnts
                    print('HDR @ %4i. MCNT %12u. Freq: %4i (X:%i). Ant: %3i. 4 bit power: PolQ: %4.2f, PolI: %4.2f' % (hdr_index, feng_unpkd_pkt['pkt_mcnt'], feng_unpkd_pkt['pkt_freq'],feng_unpkd_pkt['exp_xeng'], feng_unpkd_pkt['pkt_ant'], feng_unpkd_pkt['rms_polQ'], feng_unpkd_pkt['rms_polI']))

                    if 'Antenna%i' % feng_unpkd_pkt['pkt_ant'] not in report[f]:
                        report[f]['Antenna%i' % feng_unpkd_pkt['pkt_ant']] = 1
                    else:
                        report[f]['Antenna%i' % feng_unpkd_pkt['pkt_ant']] += 1

    print('\n\nDone with all servers.\nSummary:\n==========================')
    for k, r in six.iteritems(report):
        keys = list(report[k].keys())
        keys.sort()
        srvr = servers[r['fpga_index']]
        print('------------------------')
        print(srvr)
        print('------------------------')
        for key in keys:
            print(key,': ', r[key])
    print('==========================')

except KeyboardInterrupt:
    exit_clean()
except:
    exit_fail()

exit_clean()
