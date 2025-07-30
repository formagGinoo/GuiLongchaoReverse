function test()
	boy = {money = 200, t = 200}
	function boy.goToMarket(self ,someMoney)
		self.money = self.money - someMoney
		self.money = self.t
	end
	boy:goToMarket(100)
	local t1 = 1
	local t2 = t1
	local t3 = t2 and t1 or t1
	t1 = nil
	t1 = true
	t2 = (-(t1)) - t1 * t2 / t2 % t2 ^ t2 + t2
	t3 = {}
	t3 = {"foo","bar"}
	for k , _ in t3 do
	end
	function f0(...)
	end
	function f1(n)
		function f2(...)
			f0(...)
			n = 200
			print(#n .. "foobar")
			if not t2 then
				t1 = t1 > t2
				t1 = t2 <= t1
				t1 = t2 == t1
				t1 = t2 ~=t1
				t1 = not t2
			else
			end
		end
		return f2(300)
	end
	for k=1, f1(3) do
	end
end

return test
