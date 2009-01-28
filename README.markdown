# Speccify

## A lightweight alternative to RSpec.



## Features:

### Blazing Fast

### 100% Ruby 1.9 compatible

### Rails!

### Nested Contexts

### Sophisticated Expectations/Matchers System

### Based on [MiniTest](http://rubyforge.org/projects/bfts/)

### < 300 LOC



## Install Speccify:

> sudo gem install mhennemeyer-speccify

## Using Speccify

Create a testfile:
    
			# test_object.rb  
			
			require "rubygems"  
			require "speccify"  

			describe Object do  
			  before do  
			    @obj = Object.new  
			  end 
			
			  it "is not nil" do
			    @obj.should_not be_nil
			  end
			  
			  it "can be frozen" do
			    @obj.freeze
			    @obj.should be_frozen
			  end
			end
			
Run it with the ruby command:
			
> $ ruby test_object.rb   
>Loaded suite -  
>Started  
>..  
>Finished in 0.001820 seconds.  
> 
>2 tests, 2 assertions, 0 failures, 0 errors, 0 skips  


## Using Speccify with autotest

1. Name your testfiles test_whatever.rb
2. Start autotest
3. There is no step three ...

## Using Speccify with Rails

Use the default rails test directory/structure, testhelpers, assertions and infrastructure.  


1. sudo use_minitest yes
2. require 'speccify' in test_helper.rb
3. There is no step three ...

If you want to test a controller, just begin your examples with a description block
that takes the name of the controller as the first argument:

				describe HorstsController do
				  # Now i'm an ActionController::TestCase !
				  it "should get index" do
				    get :index
				    assert_response :success
				    assert_not_nil assigns(:horsts)
				  end
					describe "Whatever" do
					  # I'm an ActionController::TestCase, too!
					  it "should get index" do
					    get :index
					    assert_response :success
					    assert_not_nil assigns(:horsts)
					  end
					end
				end
					
I'm not sure if I should wrap the rails assertions in matchers.
Using the default rails assertions works fine.


## Built in matchers

* be_something, for any arbitrary something:  
      
        @obj.should be_something
        # passes if @obj.something? is true
       

* have(n).somethings, for any arbitrary something:

        @obj.should have(3).somethings
        # passes if @obj.somethings.length == 3

* change {something}

        lambda {@var+=1}.should change {@var}
        # passes
        lambda { }.should change {@var}
        # fails
        @var = 1
        lambda {@var+=1}.should change {@var}.from(1).to(2)
        # passes
    
* more

## DEF_MATCHER

### A simple example first:

	    def_matcher :be_nil do |given, matcher, args|
	      given.nil?
	    end
	    nil.should be_nil
	
	
The `def_matcher` method is really simple to use.  
You just provide it the name of your matcher and attach a block that defines it's behavior.
The return value of the block is a boolean that 
actually will be expected (should) or not expected (`should_not`).

There are three arguments available inside the matcher block:

### given

  This is the object that has received the should or `should_not`.

### matcher
  
This is the matcher object. You can set the failure messages as attributes on this object:
   
          def_matcher :matcher_name do |given, matcher, args|
            matcher.positive_msg = "You can see me if I am applied to should and I return a false value"
            matcher.negative_msg = "You can see me if I am applied to should_not and I return a true value"
          end 

It holds a list of all methods that have been called on the matcher (for chaining):
  
          obj.should matcher_name.some_method(4,5,6) {"and a block"}.second
          def_matcher :matcher_name do |given, matcher, args|
            # this is an ostruct that holds all information about the first method 'some_method'
            matcher.msgs[0] 
            # this is an ostruct that holds all information about the second method 'second'
            matcher.msgs[1] 
            # this is the name of the first method:
            matcher.msgs[0].name  #=> :some_method
						# this is a list of arguments that have been passed to the first method:
            matcher.msgs[0].args  #=> [4,5,6]
						# this is the block that was attached:
            matcher.msgs[0].block #=> proc {"and a block"}
          end

If there is a failure, it knows where:

          def_matcher :matcher_name do |given, matcher, args|
            matcher.loc #=> "./some/where.rb:55 ... "
          end

### args
  This is a list of all arguments that have been applied to the matcher. Like the 6 in: 
        
         (3*3).should_not be(6)

## More def_matcher examples

### A little more complex:

			def_matcher :be_in_range do |given, matcher, args|
			  range = args[1] ? (args[0]..args[1]) : args[0]
			  matcher.positive_msg = "expected #{given} to be in range (#{range})"
			  matcher.negative_msg = "expected #{given} not to be in range (#{range})"
			  range.include?(given)
			end
			2.should be_in_range(1,3)
			"m".should be_in_range("a".."z")
			
### Matchers may receive messages:

			def_matcher :have do |given, matcher, args|
			  number = args[0]
			  actual = given.send(matcher.msgs[0].name).length
			  matcher.positive_msg = "Expected #{given} to have #{actual}, but found #{number} "
			  actual == number
			end
			class Thing
			  def widgets
			    @widgets ||= []
			  end
			end
			@thing.should have(3).widgets


## Speccify vs. RSpec

### Speccify provides the parts of RSpec that actually matter (to me):

* **The familiar describe/it syntax**
* **nested contexts**
* **should/should_not**
* **matchers and custom matchers**

### Things that actually doesn't matter (to me):

* **/spec directory instead of /test**
* **`whatever_spec.rb` instead of `test_whatever.rb`**
* **custom formatters**
* **custom runners**
* **html output**
* **special commandline tools**
* **shared example groups**
* **pending examples**

			

## Problems

If using speccify with `minitest_tu_shim` and rails,  
mocha-0.9.4 causes errors because of minitest incompatibility.  
This issue is fixed in mocha's trunk and won't persist.  

## Contribution

* Bug? -> Lighthouse
* source : http://github.com/mhennemeyer/speccify
* Ideas? -> Group

## License

(The MIT License)

Copyright (c) Matthias Hennemeyer

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.