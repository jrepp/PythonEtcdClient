#l = c.module.lock.get_lock('test_lock_2')
#l.acquire(10)
#l.renew(150)
#l.release()

#with c.module.lock.get_lock('test_lock_2', 10):
#    print("In lock.")

#with c.module.lock.get_rlock('test_lock_2', 'host1', 10):
#    print("In lock 2.")

#exit(0)

# TODO: Is a lock deleted implicitly after expiration, or is it just somehow deactivated? I tried one key with the index lock, and I subsequently used the same key for a value lock, and I got a 500.

#r = c.lock.get_rlock('test_lock_3', 'proc3')
#r.acquire(30)
#r.release()
#
#r = c.lock.get_rlock('test_lock_3', 'proc3')
#r.acquire(60)
#r.release()
#
#r = c.lock.get_rlock('test_lock_3', 'proc4')
#r.acquire(30)
#r.release()

#print("Active")
#print(r.get_active_value())

#exit(0)


